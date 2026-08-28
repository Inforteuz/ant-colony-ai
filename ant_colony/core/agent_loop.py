"""
Agentic ReAct Loop.

Ilgari har bir agent LLM'ni faqat BIR marta chaqirardi va asbob natijasi modelga
qaytarilmasdi — ya'ni agent o'z ishining natijasini ko'rmasdi, xatosini tuzatmasdi,
bir necha fayl yaratmasdi. Bu modul o'sha bo'shliqni to'ldiradi:

    fikrlash -> asbob chaqirish -> natijani ko'rish -> tuzatish -> ... -> yakun

Qo'shimcha himoya choralari:
  * native function-calling ishlamasa, matndagi ```tool_call bloklari o'qiladi;
  * bir xil asbob bir xil argumentlar bilan takrorlansa, sikl aniqlanadi va uziladi;
  * har bir qadamning natijasi hisobga olinadi — QA bahosi taxminga emas,
    haqiqiy signallarga (fayl yozildi, test o'tdi) asoslanadi.
"""
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, AsyncGenerator, Optional

from ant_colony.config import AGENT_CONFIG
from ant_colony.runtime.tools import (
    AVAILABLE_TOOLS, execute_tool, get_tool_schemas, render_tool_guide,
    get_active_project_dir, walk_project_files,
)
from ant_colony.llm.client import llm_client
from ant_colony.llm.usage_ledger import usage_ledger

# Matndan asbob chaqirig'ini ajratish uchun naqshlar (native calling ishlamaganda).
_FENCED_TOOL_RE = re.compile(
    r"```(?:tool_call|json_tool_call|json)?\s*\n(\{.*?\})\s*\n?```",
    re.DOTALL
)
_THINK_RE = re.compile(r"<think(?:ing)?>(.*?)</think(?:ing)?>", re.DOTALL)
_COMPLETE_RE = re.compile(r"\bTASK[_\s]COMPLETE\b", re.IGNORECASE)

# Bir xil chaqiruv necha marta takrorlansa sikl deb hisoblanadi.
# Ilgari 3 edi — lekin `edit_file` xatosini tuzatib qayta urinsa ham chetlanardi.
# Endi 4: birinchi urunish, birinchi tuzatish, ikkinchi tuzatish, va NEXT — sikl.
_LOOP_LIMIT = 4


def split_reasoning(text: str) -> tuple[str, str]:
    """<think> bloklarini va matnli 'Here's a thinking process:' bloklarini asosiy javobdan ajratadi."""
    if not text:
        return "", ""

    thoughts = [m.strip() for m in _THINK_RE.findall(text)]
    clean = _THINK_RE.sub("", text).strip()

    # Also detect text-based reasoning (common in Nemotron, DeepSeek, Llama models without XML tags)
    reasoning_text_match = re.search(
        r"(?:^|\n)(?:Here's a thinking process|Thinking Process|Thinking Steps|Thought Process):?\s*\n([\s\S]*?)(?=\n(?:###|```|\*\*|Salom|Привет|Hello|[A-ZА-ЯЁ][a-zа-яё]+:|\{|\d+\.\s+[A-ZА-ЯЁ])|$)",
        clean,
        re.IGNORECASE
    )
    if reasoning_text_match:
        extracted = reasoning_text_match.group(0).strip()
        thoughts.append(extracted)
        clean = clean.replace(extracted, "").strip()

    return "\n\n".join(thoughts).strip(), clean


def _try_repair_tool_json(raw: str) -> Optional[Dict[str, Any]]:
    """Tool call JSON'ini xato bo'lsa tuzatib qayta parselaydi (LLM'lar tez qiladigan xatolar)."""
    try:
        s = raw
        s = re.sub(r'\bTrue\b', 'true', s)
        s = re.sub(r'\bFalse\b', 'false', s)
        s = re.sub(r'\bNone\b', 'null', s)
        s = re.sub(r',(\s*[}\]])', r'\1', s)
        return json.loads(s)
    except Exception:
        return None


def parse_text_tool_calls(text: str) -> tuple[List[Dict[str, Any]], str]:
    """
    Matndagi ```tool_call bloklaridan asbob chaqiruvlarini ajratadi.
    Bir xabarda bir nechta chaqiruv bo'lishi mumkin. Qaytadi: (chaqiruvlar, tozalangan matn).
    Broken JSON'ni ham qutqarishga urinadi.
    """
    calls: List[Dict[str, Any]] = []
    consumed: List[str] = []

    for idx, match in enumerate(_FENCED_TOOL_RE.finditer(text or "")):
        raw = match.group(1)
        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = _try_repair_tool_json(raw)
        if not isinstance(parsed, dict):
            continue
        name = parsed.get("tool") or parsed.get("action") or parsed.get("name")
        if not name or name not in AVAILABLE_TOOLS:
            continue
        args = parsed.get("params") or parsed.get("parameters") or parsed.get("arguments") or {}
        # Ba'zi modellar argumentlarni yuqori darajada beradi: {"tool": "...", "filename": "..."}
        if not args:
            args = {k: v for k, v in parsed.items()
                    if k not in ("tool", "action", "name", "params", "parameters", "arguments")}
        calls.append({"id": f"text_call_{idx}", "name": name,
                      "arguments": args if isinstance(args, dict) else {}})
        consumed.append(match.group(0))

    clean = text or ""
    for block in consumed:
        clean = clean.replace(block, "")
    return calls, clean.strip()


def _call_signature(call: Dict[str, Any]) -> str:
    try:
        return f"{call['name']}:{json.dumps(call.get('arguments', {}), sort_keys=True)[:400]}"
    except Exception:
        return f"{call['name']}:?"


def _summarize_for_model(name: str, output: Dict[str, Any]) -> str:
    """
    Asbob natijasini modelga qaytarish uchun ixcham holga keltiradi.
    Butun fayl mazmunini qayta yuborish tokenni behuda yoqadi.
    """
    if not isinstance(output, dict):
        return json.dumps({"result": str(output)[:1500]}, ensure_ascii=False)

    trimmed = dict(output)
    if name == "write_file" or name == "edit_file":
        trimmed.pop("workspace_path", None)
    if name == "list_files":
        files = trimmed.get("files", [])
        trimmed["files"] = [f.get("name") for f in files[:40]]
    if name == "read_file" and isinstance(trimmed.get("content"), str):
        trimmed["content"] = trimmed["content"][:8000]

    try:
        return json.dumps(trimmed, ensure_ascii=False)[:9000]
    except Exception:
        return str(trimmed)[:9000]


def _compact_message_history(messages: List[Dict[str, Any]], max_chars: int) -> int:
    """Trim old tool output while preserving recent tool-call relationships."""
    total = sum(len(str(message.get("content") or "")) for message in messages)
    if total <= max_chars or len(messages) <= 8:
        return 0

    saved = 0
    protected_start = 2
    protected_end = max(protected_start, len(messages) - 6)
    for message in messages[protected_start:protected_end]:
        content = message.get("content")
        if not isinstance(content, str) or len(content) <= 700:
            continue
        if message.get("role") == "tool":
            limit = 700
        elif message.get("role") == "assistant":
            limit = 400
        else:
            limit = 800
        if len(content) > limit:
            message["content"] = content[:limit] + "\n...[oldingi natija qisqartirildi]"
            saved += len(content) - len(message["content"])
    return saved


def _project_snapshot(project_dir: Path) -> str:
    """Give an agent a small map of an existing project before it chooses tools."""
    files, truncated = walk_project_files(project_dir, limit=80, max_depth=4)
    paths = [relative for _path, relative in files]
    if not paths:
        return ""
    important_names = {"README.md", "package.json", "pyproject.toml", "requirements.txt", "docker-compose.yml", "Makefile"}
    important = [path for path in paths if Path(path).name in important_names]
    listed = (important + [path for path in paths if path not in important])[:45]
    suffix = "\nFayllar ro'yxati cheklangan; kerak bo'lsa `list_dir` bilan kengaytiring." if truncated else ""
    return "Mavjud loyiha fayllari:\n" + "\n".join(f"- {path}" for path in listed) + suffix


class AgentRunResult:
    """Bitta agent yugurishining natijasi va o'lchanadigan signallari."""

    def __init__(self):
        self.final_text: str = ""
        self.reasoning: str = ""
        self.steps: int = 0
        self.tool_calls: int = 0
        self.tool_failures: int = 0
        self.files_written: List[str] = []
        self.commands_run: List[str] = []
        self.models_used: List[str] = []
        self.usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0}
        self.error: Optional[str] = None
        self.hit_step_limit: bool = False
        self.duration_s: float = 0.0
        self.context_chars_saved: int = 0

    @property
    def produced_artifacts(self) -> bool:
        return bool(self.files_written)

    @property
    def tool_success_rate(self) -> float:
        if self.tool_calls == 0:
            return 0.0
        return (self.tool_calls - self.tool_failures) / self.tool_calls

    def as_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "tool_failures": self.tool_failures,
            "tool_success_rate": round(self.tool_success_rate, 3),
            "files_written": self.files_written,
            "commands_run": self.commands_run[:10],
            "models_used": self.models_used,
            "usage": self.usage,
            "hit_step_limit": self.hit_step_limit,
            "duration_s": round(self.duration_s, 2),
            "context_chars_saved": self.context_chars_saved,
            "error": self.error,
        }


async def run_agent(
    *,
    station: str,
    agent_name: str,
    model_id: str,
    role_md: str,
    task: str,
    context: str = "",
    tool_names: Optional[List[str]] = None,
    max_steps: Optional[int] = None,
    temperature: float = 0.2,
    max_tokens: int = 8192,
    custom_keys: Optional[Dict[str, str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Agentni asbob-qadam sikli bilan yugurtiradi va hodisalar oqimini beradi.

    Oxirgi hodisa har doim `{"type": "agent_done", "result": AgentRunResult}` bo'ladi —
    chaqiruvchi shu natijadan foydalanadi.
    """
    t_start = time.time()
    max_steps = max_steps or AGENT_CONFIG["max_tool_steps"]
    tool_names = tool_names or list(AVAILABLE_TOOLS.keys())
    schemas = get_tool_schemas(tool_names)
    result = AgentRunResult()

    project_dir = get_active_project_dir()
    project_snapshot = _project_snapshot(project_dir)
    system_prompt = (
        f"{role_md}\n\n"
        f"{render_tool_guide(tool_names)}\n\n"
        "## Ish tartibi (qat'iy)\n"
        f"1. Ishchi papka: `{project_dir}`. Barcha fayllarni shu papkaga nisbatan yozing.\n"
        "2. Kodni javob matnida tashlab ketmang — har bir faylni `write_file` bilan HAQIQATAN yozing.\n"
        "3. Faylni tahrirlashdan oldin `read_file` bilan o'qing; kichik o'zgarish uchun `edit_file` ishlating.\n"
        "4. Yozganingizni tekshirib ko'ring (`execute_python` yoki `run_shell_command`).\n"
        "5. Asbob xato qaytarsa, xatoni o'qib tuzating — bir xil chaqiruvni takrorlamang.\n"
        f"6. Sizda ko'pi bilan {max_steps} qadam bor. Qadamlarni tejab ishlating.\n"
        "7. Hammasi tayyor bo'lgach, qisqa xulosa yozib `TASK_COMPLETE` bilan yakunlang.\n"
    )

    user_content = f"## Topshiriq\n{task}"
    if context:
        user_content += f"\n\n## Kontekst\n{context}"
    if project_snapshot:
        user_content += f"\n\n## Loyiha snapshot\n{project_snapshot}"

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    seen_signatures: Dict[str, int] = {}
    current_model = model_id

    for step in range(max_steps):
        result.steps = step + 1
        result.context_chars_saved += _compact_message_history(
            messages, AGENT_CONFIG.get("context_max_chars", 26000)
        )

        # Har bir chaqiruv token daftariga AYNAN shu agent nomi bilan tushadi —
        # shunda "qaysi agent qancha token yedi" savoliga aniq javob bo'ladi.
        # Doira faqat `await` atrofida: parallel agentlar bir-birining
        # kontekstini ustiga yozib yubormasligi uchun.
        with usage_ledger.agent_scope(agent_name, role=station, phase="execution"):
            response = await llm_client.complete(
                current_model, messages,
                tools=schemas,
                temperature=temperature,
                max_tokens=max_tokens,
                custom_keys=custom_keys,
            )

        if not response["success"]:
            result.error = response.get("error", "LLM chaqiruvi muvaffaqiyatsiz")
            yield {"type": "agent_error", "station": station,
                   "agent_name": agent_name, "error": result.error}
            break

        used = response["model_used"]
        if used not in result.models_used:
            result.models_used.append(used)
        # Zaxira model ishlagan bo'lsa, keyingi qadamlarda ham shuni ishlatamiz.
        current_model = used

        usage = response.get("usage", {})
        for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
            result.usage[key] += usage.get(key, 0) or 0

        inline_reasoning, text = split_reasoning(response["text"])
        reasoning = (response.get("reasoning") or "") + ("\n" + inline_reasoning if inline_reasoning else "")
        reasoning = reasoning.strip()

        tool_calls = list(response.get("tool_calls") or [])
        native_calls = bool(tool_calls)
        if not tool_calls:
            # Native calling ishlamadi — matndagi bloklardan o'qiymiz.
            tool_calls, text = parse_text_tool_calls(text)

        if reasoning:
            result.reasoning = reasoning
            yield {
                "type": "reasoning", "station": station, "agent_name": agent_name,
                "reasoning_text": reasoning[:4000],
                "reasoning_tokens": usage.get("reasoning_tokens") or (len(reasoning.split()) * 4 // 3),
                "model": used, "step": result.steps,
            }

        if response.get("fallback_used"):
            yield {
                "type": "model_fallback", "station": station, "agent_name": agent_name,
                "requested_model": model_id, "actual_model": used,
                "message": f"Модель `{model_id}` не ответила — переключено на `{used}`",
            }

        # --- Asbob chaqiruvlari yo'q => agent yakunlandi ---
        if not tool_calls:
            result.final_text = text
            yield {
                "type": "agent_message", "station": station, "agent_name": agent_name,
                "content": text, "model": used, "step": result.steps,
                "usage": usage, "duration_ms": response.get("duration_ms", 0),
            }
            break

        # Assistant xabarini tarixga qo'shamiz.
        # Chaqiruvlar NATIVE bo'lsa — provayder kutgan `tool_calls` formatida yuboramiz.
        # Matndan ajratilgan bo'lsa — sun'iy `tool_calls` yasamaymiz: qat'iy
        # endpointlar o'zi generatsiya qilmagan tool_call_id'ni rad etishi mumkin.
        # Bunday holatda natijalarni oddiy `user` xabari sifatida qaytaramiz.
        if native_calls:
            # OpenAI-compatible provayderlar tool_calls bilan bo'sh content'ni None ga aylantirishni istaydi
            asst_content = text if (text and text.strip()) else None
            messages.append({"role": "assistant", "content": asst_content, "tool_calls": tool_calls})
        else:
            calls_repr = "\n".join(
                f'```tool_call\n{{"tool": "{c["name"]}", "params": {json.dumps(c.get("arguments", {}), ensure_ascii=False)}}}\n```'
                for c in tool_calls
            )
            messages.append({"role": "assistant", "content": (text + "\n\n" + calls_repr).strip()})

        stop_after_tools = False
        text_results: List[str] = []

        for call in tool_calls:
            name = call["name"]
            args = call.get("arguments", {})
            signature = _call_signature(call)
            seen_signatures[signature] = seen_signatures.get(signature, 0) + 1

            # Sikl aniqlanishi: bir xil chaqiruv qayta-qayta — modelga to'xtash signali.
            if seen_signatures[signature] >= _LOOP_LIMIT:
                loop_msg = json.dumps({
                    "success": False,
                    "error": (f"`{name}` aynan shu argumentlar bilan {seen_signatures[signature]} marta "
                              "chaqirildi — sikl aniqlandi. Boshqa yondashuvni sinang yoki "
                              "ishni yakunlab `TASK_COMPLETE` yozing.")
                }, ensure_ascii=False)
                if native_calls:
                    messages.append({"role": "tool", "tool_call_id": call.get("id", "call_0"),
                                     "name": name, "content": loop_msg})
                else:
                    text_results.append(f"### `{name}` natijasi\n{loop_msg}")
                result.tool_calls += 1
                result.tool_failures += 1
                yield {
                    "type": "agent_warning", "station": station, "agent_name": agent_name,
                    "message": f"Sikl aniqlandi: `{name}` takrorlanmoqda — uzildi",
                }
                stop_after_tools = True
                continue

            yield {
                "type": "station_action", "station": station, "agent_name": agent_name,
                "action_type": "tool_call", "tool": name, "params": args, "step": result.steps,
            }

            t_tool = time.time()
            output = execute_tool(name, args)
            tool_ms = round((time.time() - t_tool) * 1000)

            result.tool_calls += 1
            ok = bool(output.get("success", False)) if isinstance(output, dict) else False
            if not ok:
                result.tool_failures += 1

            if ok and name in ("write_file", "edit_file"):
                fname = output.get("filename")
                if fname and fname not in result.files_written:
                    result.files_written.append(fname)
            if name == "run_shell_command" and args.get("command"):
                result.commands_run.append(args["command"])

            yield {
                "type": "station_action", "station": station, "agent_name": agent_name,
                "action_type": "tool_result", "tool": name, "output": output,
                "success": ok, "duration_ms": tool_ms, "step": result.steps,
            }

            summary = _summarize_for_model(name, output)
            if native_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", "call_0"),
                    "name": name,
                    "content": summary,
                })
            else:
                text_results.append(f"### `{name}` natijasi\n{summary}")

        if text_results:
            messages.append({
                "role": "user",
                "content": ("Asboblar bajarildi. Natijalar:\n\n" + "\n\n".join(text_results)
                            + "\n\nNatijalarni tahlil qilib davom eting.")
            })

        if stop_after_tools:
            # Keyingi qadamda model xulosa yozishi kerak — asboblarsiz.
            messages.append({
                "role": "user",
                "content": "Asbob chaqirmasdan, bajarilgan ishning qisqa xulosasini yozing va `TASK_COMPLETE` bilan yakunlang."
            })

        if _COMPLETE_RE.search(text or ""):
            result.final_text = text
            break
    else:
        result.hit_step_limit = True

    # Qadam limitiga yetdi, lekin xulosa yo'q — bitta yakuniy so'rov yuboramiz.
    if not result.final_text and not result.error:
        messages.append({
            "role": "user",
            "content": ("Qadam limiti tugadi. Asbob chaqirmasdan, nima qilganingiz, qaysi fayllar "
                        "yaratilgani va nima tugallanmaganini qisqa bayon qiling.")
        })
        with usage_ledger.agent_scope(agent_name, role=station, phase="wrapup"):
            wrap = await llm_client.complete(
                current_model, messages, tools=None,
                temperature=0.1, max_tokens=1500, custom_keys=custom_keys
            )
        if wrap["success"]:
            _, clean = split_reasoning(wrap["text"])
            result.final_text = clean
            for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
                result.usage[key] += wrap.get("usage", {}).get(key, 0) or 0
    # Agar agent asbob chaqirmasdan, kodni to'g'ridan-to'g'ri javob matnida bergan bo'lsa —
    # barcha dasturlash tillari (Python, Go, Node, TS, PHP, Rust, SQL, Docker, HTML)
    # bo'yicha kod bloklarini avtomatik ajratib olib, fayllarga saqlaymiz.
    if not result.files_written and result.final_text:
        raw_text = result.final_text
        from ant_colony.runtime.tools import write_file

        lang_mappings = [
            (r"```html\s*\n([\s\S]*?)```", "index.html"),
            (r"```css\s*\n([\s\S]*?)```", "style.css"),
            (r"```(?:typescript|ts)\s*\n([\s\S]*?)```", "app.ts"),
            (r"```(?:javascript|js)\s*\n([\s\S]*?)```", "script.js"),
            (r"```python\s*\n([\s\S]*?)```", "main.py"),
            (r"```go\s*\n([\s\S]*?)```", "main.go"),
            (r"```(?:rust|rs)\s*\n([\s\S]*?)```", "main.rs"),
            (r"```php\s*\n([\s\S]*?)```", "index.php"),
            (r"```sql\s*\n([\s\S]*?)```", "schema.sql"),
            (r"```(?:dockerfile|docker)\s*\n([\s\S]*?)```", "Dockerfile"),
            (r"```(?:yaml|yml)\s*\n([\s\S]*?)```", "docker-compose.yml"),
            (r"```(?:bash|sh)\s*\n([\s\S]*?)```", "run.sh"),
            (r"```json\s*\n([\s\S]*?)```", "package.json"),
        ]

        for pattern, default_filename in lang_mappings:
            m = re.search(pattern, raw_text, re.IGNORECASE)
            if m:
                w = write_file(default_filename, m.group(1).strip())
                if w.get("success") and default_filename not in result.files_written:
                    result.files_written.append(default_filename)

    # --- Post-completion sanity check ---
    # Agar agent kod loyihasi (write_file'lar bo'lgan) yozgan bo'lsa,
    # avtomatik sintaksis tekshiruvi yugurtiramiz. Xatolar topilsa — bitta
    # tuzatish urinishi beramiz. Bu agent'ning "TASK_COMPLETE"'ini haqiqiy natijaga bog'laydi.
    if result.files_written and not result.error:
        try:
            from ant_colony.runtime.tools import verify_code_syntax
            check = verify_code_syntax()
            if check.get("issues_count", 0) > 0:
                issues = check.get("issues") or []
                # Agentga sinov natijasini beramiz va bir yakuniy tuzatish urinishi
                issues_txt = "\n".join(
                    f"- **{i.get('file', '?')}**"
                    + (f" (qator {i['line']})" if i.get('line') else "")
                    + f": {i.get('message', '')[:200]}"
                    for i in issues[:8]
                )
                yield {
                    "type": "agent_warning", "station": station, "agent_name": agent_name,
                    "message": f"Sintaksis tekshiruvi {check['issues_count']} xato topdi — avto-tuzatish urinishi",
                }
                messages.append({
                    "role": "user",
                    "content": (
                        "**MAJBURIY TUZATISH**: TASK_COMPLETE yakunlandi, lekin avtomatik sintaksis "
                        f"tekshiruvi quyidagi xatolarni aniqladi:\n\n{issues_txt}\n\n"
                        "Har bir xatoni `read_file` bilan o'qib, `edit_file` yoki `write_file` bilan "
                        "tuzating. Xatolar tugagach `TASK_COMPLETE` bilan yakunlang."
                    )
                })
                # Tuzatish uchun 5 qadam beramiz
                fix_max = min(5, AGENT_CONFIG.get("max_tool_steps", 12))
                for fix_step in range(fix_max):
                    result.steps += 1
                    with usage_ledger.agent_scope(agent_name, role=station, phase="self_repair"):
                        fix_resp = await llm_client.complete(
                            current_model, messages,
                            tools=schemas,
                            temperature=0.1, max_tokens=max_tokens,
                            custom_keys=custom_keys,
                        )
                    if not fix_resp["success"]:
                        break
                    fix_text = fix_resp["text"] or ""
                    fix_calls = list(fix_resp.get("tool_calls") or [])
                    if not fix_calls:
                        fix_calls, fix_text = parse_text_tool_calls(fix_text)
                    for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
                        result.usage[key] += fix_resp.get("usage", {}).get(key, 0) or 0
                    if not fix_calls:
                        result.final_text = (result.final_text or "") + "\n\n" + fix_text
                        break
                    if fix_resp.get("tool_calls"):
                        messages.append({"role": "assistant", "content": fix_text, "tool_calls": fix_calls})
                    else:
                        calls_repr = "\n".join(
                            f'```tool_call\n{{"tool": "{c["name"]}", "params": {json.dumps(c.get("arguments", {}), ensure_ascii=False)}}}\n```'
                            for c in fix_calls
                        )
                        messages.append({"role": "assistant", "content": (fix_text + "\n\n" + calls_repr).strip()})
                    fix_text_results = []
                    for fc in fix_calls:
                        fn = fc["name"]; fa = fc.get("arguments", {})
                        fo = execute_tool(fn, fa)
                        result.tool_calls += 1
                        if not (isinstance(fo, dict) and fo.get("success")):
                            result.tool_failures += 1
                        elif fn in ("write_file", "edit_file"):
                            fname = fo.get("filename")
                            if fname and fname not in result.files_written:
                                result.files_written.append(fname)
                        yield {
                            "type": "station_action", "station": station, "agent_name": agent_name,
                            "action_type": "tool_result", "tool": fn, "output": fo,
                            "success": bool(fo.get("success")), "step": result.steps,
                        }
                        fs = _summarize_for_model(fn, fo)
                        if fix_resp.get("tool_calls"):
                            messages.append({"role": "tool", "tool_call_id": fc.get("id", "call_0"),
                                             "name": fn, "content": fs})
                        else:
                            fix_text_results.append(f"### `{fn}` natijasi\n{fs}")
                    if fix_text_results:
                        messages.append({"role": "user",
                                         "content": "Asboblar natijasi:\n\n" + "\n\n".join(fix_text_results)})
                    if _COMPLETE_RE.search(fix_text):
                        break
                # Oxirgi tekshiruv
                final_check = verify_code_syntax()
                if final_check.get("issues_count", 0) == 0:
                    yield {
                        "type": "agent_message", "station": station, "agent_name": agent_name,
                        "content": "✓ Sintaksis xatolari avtomatik tuzatildi.",
                        "step": result.steps,
                    }
        except Exception as e:
            yield {
                "type": "agent_warning", "station": station, "agent_name": agent_name,
                "message": f"Post-completion tekshiruvi xatosi (fatal emas): {e}",
            }

    result.duration_s = time.time() - t_start
    yield {"type": "agent_done", "station": station, "agent_name": agent_name,
           "result": result, "metrics": result.as_dict()}
