"""
Agent Engine: Central PM Orchestrator with Desktop Projects (04_Loyihalar), Full Terminal Access,
Prompt Caching, and Live CEO Executive Briefing.

Orkestratsiya oqimi:
    1. PM tahlil qiladi va tuzilmali (JSON) reja beradi — shu jumladan qaysi
       mutaxassis rol kerakligini o'zi tanlaydi.
    2. Mutaxassis agent HAQIQIY asbob-qadam siklida ishlaydi (agent_loop),
       fayllarni yozadi, tekshiradi, xatolarni tuzatadi.
    3. QA va Xavfsizlik auditori PARALLEL ishlaydi — ikkalasi ham fayllarni
       o'qish va testlarni yurgizish asboblariga ega.
    4. Baho past bo'lsa — tuzatish (repair) sikli: mutaxassis QA topgan
       kamchiliklarni tuzatadi, QA qayta tekshiradi.
    5. Model reytingi taxminga emas, o'lchangan signallarga qarab yangilanadi.
"""
import re
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, AsyncGenerator, Optional, Tuple

from config import (
    PROVIDERS, MODELS_CATALOG, WORKSPACE_DIR, PROJECTS_BASE_DIR,
    WORKSTATIONS, AGENT_CONFIG,
)
from tools import (
    AVAILABLE_TOOLS, set_active_project_dir, get_active_project_dir, list_dir,
)
from models_hub import models_hub
from skill_matrix import skill_matrix, DEFAULT_ROLE_DEFINITIONS
from prompt_cache import prompt_cache
from llm_client import llm_client
from agent_loop import run_agent, split_reasoning, AgentRunResult

# Loyiha nomini yasashda tashlab yuboriladigan yordamchi so'zlar.
_STOPWORDS = {
    "menga", "uchun", "bilan", "qilib", "qil", "qiling", "yoz", "yozing", "yasa",
    "yasab", "ber", "bering", "kerak", "iltimos", "va", "ham", "bir", "bu",
    "make", "create", "build", "write", "please", "a", "an", "the", "for", "with",
}

# Vazifa matnidan mutaxassis rolni topish uchun kalit so'zlar.
_ROLE_KEYWORDS: Dict[str, List[str]] = {
    "frontend_architect": ["html", "css", "frontend", "sahifa", "veb", "web", "react", "vue", "brauzer", "responsive", "landing"],
    "ui_designer": ["dizayn", "design", "animatsiya", "animation", "canvas", "svg", "grafik", "ui", "ux", "rang", "palitra"],
    "backend_engineer": ["api", "backend", "server", "fastapi", "flask", "express", "endpoint", "rest", "websocket", "mikroservis"],
    "database_architect": ["baza", "database", "sql", "postgres", "mysql", "sqlite", "schema", "jadval", "migration", "mongo"],
    "algorithm_solver": ["algoritm", "algorithm", "matematik", "hisobla", "optimallash", "leetcode", "murakkablik", "formula", "graf"],
    "qa_test_automation": ["test", "pytest", "unit test", "jest", "sinov", "tekshir"],
    "devops_deployer": ["deploy", "docker", "ci/cd", "kubernetes", "nginx", "script", "bash", "avtomatlash"],
    "security_auditor": ["xavfsizlik", "security", "zaiflik", "vulnerability", "audit", "shifrlash", "autentifikatsiya"],
    "data_miner_researcher": ["tadqiqot", "research", "ma'lumot yig", "scraping", "tahlil", "hisobot", "statistika"],
    "performance_optimizer": ["tezlik", "performance", "optimallashtir", "sekin", "profiling", "xotira", "keshlash"],
    "system_troubleshooter": ["xato", "bug", "ishlamayapti", "tuzat", "debug", "nosozlik", "crash", "fix"],
    "mobile_developer": [
        "flutter", "dart", "react native", "react-native", "expo",
        "mobil", "mobile", "android", "ios", "iphone", "smartfon", "apk", "ipa",
        "swift", "kotlin", "мобильн", "приложение для телефон"
    ],
    "microservices_architect": [
        "mikroservis", "microservice", "microservices", "grpc", "kafka", "rabbitmq",
        "kubernetes", "k8s", "service mesh", "docker-compose", "istio",
        "распределённ", "event-driven", "cqrs", "saga pattern"
    ],
    "blockchain_dev": [
        "blockchain", "smart contract", "smartkontrakt", "solidity", "vyper", "foundry", "hardhat",
        "web3", "web 3", "erc-20", "erc20", "erc-721", "nft", "defi", "dao",
        "ethereum", "polygon", "solana", "aptos", "cosmos",
        "смарт-контракт", "блокчейн", "крипто"
    ],
}

_SCORE_RE = re.compile(r"(?:Baho|Ball|Score|Reyting)\s*[:=]?\s*(\d{1,3})\s*(?:/\s*100)?", re.IGNORECASE)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(\{.*?\})\s*\n?```", re.DOTALL)


def sanitize_slug(text: str) -> str:
    """Generate a clean directory slug for the project on Desktop."""
    clean = re.sub(r"[^a-zA-Z0-9\s_Ѐ-ӿ'-]", " ", (text or "").lower())
    words = [w for w in clean.split() if w and w not in _STOPWORDS and len(w) > 1]
    slug = "_".join(words[:5]) if words else f"loyiha_{int(time.time())}"
    return slug[:60].strip("_") or f"loyiha_{int(time.time())}"


def allocate_project_dir(task_prompt: str, preferred_name: Optional[str] = None) -> Path:
    """
    Loyiha papkasini ajratadi. Agar shu nomdagi papka allaqachon fayllar bilan
    to'lgan bo'lsa, yangi raqamli variant beriladi — ilgari bir xil topshiriq
    ikki marta berilganda avvalgi ish ustiga yozilib ketardi.
    """
    base_slug = sanitize_slug(preferred_name or task_prompt)
    candidate = PROJECTS_BASE_DIR / base_slug
    suffix = 2
    while candidate.exists() and any(
        f.is_file() and not f.name.startswith(".") for f in candidate.iterdir()
    ):
        candidate = PROJECTS_BASE_DIR / f"{base_slug}_{suffix}"
        suffix += 1
        if suffix > 50:
            candidate = PROJECTS_BASE_DIR / f"{base_slug}_{int(time.time())}"
            break
    return candidate


def get_workspace_projects_summary() -> str:
    """Ishchi muhitdagi (PROJECTS_BASE_DIR) barcha haqiqiy loyihalarni skanerlaydi va sanasi bo'yicha saralaydi."""
    try:
        from pathlib import Path
        base = Path(PROJECTS_BASE_DIR)
        if not base.exists():
            return "Ishchi muhitda hozircha hech qanday loyiha papkasi mavjud emas."

        entries = []
        for p in base.iterdir():
            if p.is_dir() and not p.name.startswith('.') and p.name not in ('node_modules', '__pycache__', 'temp_workspace'):
                mtime = p.stat().st_mtime
                files = [f.name for f in p.iterdir() if f.is_file() and not f.name.startswith('.')]
                entries.append({
                    "name": p.name,
                    "mtime": mtime,
                    "mtime_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
                    "files": files[:8],
                    "path": str(p)
                })

        entries.sort(key=lambda x: x["mtime"], reverse=True)
        if not entries:
            return "Ishchi muhitda hozircha hech qanday loyiha papkasi mavjud emas."

        lines = ["Haqiqiy ishchi muhitdagi loyihalar (eng oxirgisidan boshlab / от самого последнего):"]
        for idx, e in enumerate(entries[:10], 1):
            f_list = ", ".join(e["files"]) if e["files"] else "bo'sh papka"
            lines.append(f"{idx}. Papka: `{e['name']}` ({e['mtime_str']}) — Fayllar: [{f_list}]")
        return "\n".join(lines)
    except Exception as err:
        return f"Loyihalarni skanerlashda xatolik: {err}"


def is_code_creation_intent(text: str) -> bool:
    """Foydalanuvchi haqiqatan yangi dasturiy kod/loyiha yaratishni so'rayaptimi yoki savol beryaptimi?"""
    t = (text or "").lower().strip()
    if not t:
        return False

    # 1. Aniq savol belgilari yoki umumiy suhbat
    question_indicators = [
        "?", "nima", "qanday", "nega", "qachon", "kim", "qaysi", "qanaqa", "bormi", "bila olasanmi",
        "tushuntir", "farqi", "haqida", "maslahat", "fikring", "aytib ber", "sanab ber", "qaysi biri",
        "eshityapsanmi", "taniysanmi", "eslaysanmi", "qayerda", "qanaqangi", "qanday qilib",
        "что", "как", "почему", "зачем", "где", "какой", "какие", "когда", "кто", "ли",
        "объясни", "расскажи", "в чем разница", "посоветуй", "подскажи", "каково", "помнишь",
        "what", "how", "why", "when", "who", "which", "explain", "tell me", "difference", "advice"
    ]

    # 2. Kod va loyiha yaratish/yozish buyruqlari
    creation_verbs = [
        "yarat", "yoz", "tuz", "yasa", "qur", "ishlab chiq", "dasturla", "kodini yoz", "generatsiya qil",
        "ochib ber", "tayyorla", "loyihasini tuz", "script yoz", "sayt yarat", "bot yoz", "api yoz",
        "создай", "напиши", "разработай", "сделай", "построй", "запрограммируй", "собери", "сгенерируй",
        "подготовь", "создать", "написать", "разработать", "сделать", "построить", "собрать",
        "create", "build", "write", "develop", "make", "code", "generate", "implement", "scaffold"
    ]

    has_creation_verb = any(_keyword_matches(v, t) for v in creation_verbs)
    has_question_word = any(q in t for q in question_indicators) or t.endswith("?")

    # Agar savol so'zi bo'lsa va to'g'ridan-to'g'ri yaratish buyrug'i bo'lmasa -> 100% suhbat/savol
    if has_question_word and not has_creation_verb:
        return False

    # Agar yaratish buyrug'i bo'lsa -> kod loyihasi
    if has_creation_verb:
        return True

    return False


def is_conversational_query(text: str) -> bool:
    """Tekshiradi: topshiriq savol/suhbatmi (kod loyihasi emasmi)?"""
    return not is_code_creation_intent(text)


def detect_query_lang(text: str) -> str:
    """Foydalanuvchi topshirig'i ruscha, o'zbekcha yoki inglizchami?"""
    t = (text or "").lower()
    cyrillic_chars = sum(1 for c in t if '\u0400' <= c <= '\u04FF')
    if cyrillic_chars >= 3:
        return "ru"
    uz_words = ["qanday", "nima", "qiling", "yarat", "kerak", "uchun", "bilan", "qo'lingdan", "salom", "loyiha"]
    if any(w in t for w in uz_words):
        return "uz"
    return "ru" if cyrillic_chars > 0 else "uz"


def _keyword_matches(kw: str, text: str) -> bool:
    """
    Kalit so'z matnda so'z chegarasi bilan uchraydimi?
    Oldingi `kw in text` `api` ni `napiši` ichida topib, noto'g'ri rolga yo'naltirar edi.
    Ko'p so'zdan iborat kalitlar (`react native`) uchun ham ishlaydi.
    """
    kw = kw.lower()
    # Regex maxsus belgilarni escape qilamiz — `react-native`, `k8s`, `c++` kabilarni qo'llash uchun.
    pattern = r"(?<![a-zA-Z0-9_Ѐ-ӿ])" + re.escape(kw) + r"(?![a-zA-Z0-9_Ѐ-ӿ])"
    return re.search(pattern, text) is not None


def select_specialist_role(task_prompt: str) -> str:
    """
    Vazifa matnidan mutaxassis rolni tanlaydi.

    Ilgari bu faqat ikki variantli qattiq shart edi ("html/css/animat" bo'lsa
    frontend, aks holda backend) — 12 ta rolning 10 tasi hech qachon ishlatilmasdi.
    Endi so'z chegarasi bo'yicha moslashtiradi va aniqroq rollarni afzal ko'radi.
    """
    text = (task_prompt or "").lower()
    scores: Dict[str, int] = {}
    for role_id, keywords in _ROLE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if _keyword_matches(kw, text))
        if hits:
            scores[role_id] = hits
    if not scores:
        return "backend_engineer"
    # Teng bal bo'lganda ixtisoslashgan (mobile/blockchain/microservices)
    # umumiy backend/frontend'dan ustunroq — aks holda umumiy rollar har doim g'olib.
    _generic = {"backend_engineer", "frontend_architect"}
    def _rank(item):
        rid, sc = item
        return (sc, 0 if rid in _generic else 1)
    return max(scores.items(), key=_rank)[0]


def _try_repair_json(raw: str) -> Optional[Dict[str, Any]]:
    """
    LLM'lar tez-tez qiladigan xatolarni tuzatib JSON'ni qayta parselaydi:
      * yakuniy vergul: `{"a": 1,}` → `{"a": 1}`
      * bir tirnoqli kalitlar: `{'a': 1}` → `{"a": 1}`  (faqat ehtiyot bilan)
      * ortiqcha kod izohlari `// ...` va `# ...`
      * `True`/`False`/`None` (Python) → `true`/`false`/`null`
    """
    try:
        s = raw
        # Python bool/None → JSON
        s = re.sub(r'\bTrue\b', 'true', s)
        s = re.sub(r'\bFalse\b', 'false', s)
        s = re.sub(r'\bNone\b', 'null', s)
        # Yakuniy vergullarni olib tashlaymiz (obyekt yoki massiv oxirida)
        s = re.sub(r',(\s*[}\]])', r'\1', s)
        # `// ...` izohlar (bir qatorli). Diqqat: url ichidagi `//` ga tegmaslik uchun oldida bo'sh joy talab qilamiz.
        s = re.sub(r'(?m)(^|\s)//[^\n]*', r'\1', s)
        # `# ...` izohlar (bir qatorli, faqat qator boshida)
        s = re.sub(r'(?m)^\s*#[^\n]*', '', s)
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """
    Javob matnidan birinchi to'g'ri JSON obyektini ajratadi.
    Bir necha strategiya bo'yicha urinadi: fenced blok, matndagi balanced brace,
    keyin xatoli JSON'ni tuzatib qayta urinadi.
    """
    text = text or ""

    # 1. Fenced ```json bloklari (barcha topilganlar tekshiriladi)
    for match in _JSON_BLOCK_RE.finditer(text):
        raw = match.group(1)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            repaired = _try_repair_json(raw)
            if repaired:
                return repaired

    # 2. Balanced brace scanner — string va escape'larni hisobga oladi
    #    (`text.find("{")` ... `text.rfind("}")` string ichidagi `}` da xato beradi)
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start:i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        repaired = _try_repair_json(candidate)
                        if repaired:
                            return repaired
                    start = -1  # keyingi obyektni sinaymiz

    return None


def extract_score(text: str, default: Optional[float] = None) -> Optional[float]:
    match = _SCORE_RE.search(text or "")
    if not match:
        return default
    try:
        return max(0.0, min(100.0, float(match.group(1))))
    except Exception:
        return default


async def merge_event_streams(streams: List[AsyncGenerator[Dict[str, Any], None]]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Bir nechta agent oqimini bittaga qo'shadi — agentlar PARALLEL ishlaydi,
    hodisalar esa tayyor bo'lishi bilan darhol uzatiladi.
    """
    queue: asyncio.Queue = asyncio.Queue()
    sentinel = object()

    async def pump(gen: AsyncGenerator[Dict[str, Any], None]):
        try:
            async for event in gen:
                await queue.put(event)
        except Exception as e:
            await queue.put({"type": "agent_error", "error": f"{type(e).__name__}: {e}"})
        finally:
            await queue.put(sentinel)

    tasks = [asyncio.create_task(pump(g)) for g in streams]
    remaining = len(tasks)
    try:
        while remaining > 0:
            item = await queue.get()
            if item is sentinel:
                remaining -= 1
                continue
            yield item
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def sanitize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    SSE ga uzatishdan oldin JSON'ga aylanmaydigan obyektlarni olib tashlaydi
    (`agent_done` ichidagi AgentRunResult).
    """
    if "result" in event and isinstance(event.get("result"), AgentRunResult):
        clean = {k: v for k, v in event.items() if k != "result"}
        return clean
    return event


class AgentEngine:
    def __init__(self):
        pass

    # --- Orqaga moslik: eski nomdagi metod hali ham ishlaydi ---
    async def call_llm_resilient(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        enable_reasoning: bool = True,
        use_cache: bool = False,
        custom_keys: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Eski API shakli — endi `llm_client` ustidagi yupqa qobiq."""
        res = await llm_client.complete(
            model_id, messages, temperature=temperature,
            max_tokens=max_tokens, use_cache=use_cache, custom_keys=custom_keys
        )
        res["raw_message"] = {"role": "assistant", "content": res.get("text", "")}
        return res

    def extract_reasoning_and_content(self, raw_message: Dict[str, Any]) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        """Eski API shakli — `agent_loop` funksiyalari ustidagi qobiq."""
        from agent_loop import parse_text_tool_calls
        content = raw_message.get("content", "") or ""
        reasoning, clean = split_reasoning(content)
        calls, clean = parse_text_tool_calls(clean)
        tool_call = {"tool": calls[0]["name"], "params": calls[0]["arguments"]} if calls else None
        return reasoning, clean, tool_call

    # --- PM: tuzilmali reja ---
    async def _plan_with_pm(
        self, task_prompt: str, pm_model: str, pm_md: str,
        default_role: str, custom_keys: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        role_menu = "\n".join(
            f"- `{r['id']}` — {r['description']}" for r in DEFAULT_ROLE_DEFINITIONS
            if r["id"] != "pm_orchestrator"
        )

        ws_summary = get_workspace_projects_summary()

        # PM uzoq muddatli xotira konteksti — oldingi loyihalar, kelajakdagi rejalar
        pm_mem_context = ""
        try:
            from pm_memory import get_memory
            mem = get_memory()
            if mem:
                snippet = mem.as_context_snippet(max_projects=5)
                if snippet:
                    pm_mem_context = f"\n## MENIN UZOQ MUDDATLI XOTIRAM (avvalgi sessiyalardan):\n{snippet}\n\n"
        except Exception:
            pass

        prompt = (
            f"Foydalanuvchi topshirig'i / Запрос пользователя: \"{task_prompt}\"\n\n"
            "Siz Ant Colony AI universal agentlar platformasining Bosh Project Managerisiz.\n"
            f"## ISHCHI MUHIT VA MAVJUD LOYIHALAR TARIXI (FAQAT HAQIQIY FAKTLAR):\n{ws_summary}\n\n"
            + pm_mem_context +
            "Mavjud mutaxassis rollar:\n"
            f"{role_menu}\n\n"
            "TALABLAR / ТРЕБОВАНИЯ:\n"
            "1. MUHIM TIL QOIDASI / ЯЗЫКОВОЕ ПРАВИЛО (CRITICAL):\n"
            "   Foydalanuvchi xabarida qaysi tildan foydalangan bo'lsa (ruscha, o'zbekcha, inglizcha va h.k.), "
            "rejangizni, tahlilingizni va javobingizni AYNAN O'SHA TILDA yozing. "
            "Если пользователь написал по-русски — отвечайте по-русски. Agar o'zbekcha yozgan bo'lsa — o'zbek tilida javob bering. If English — reply in English.\n\n"
            "2. AGAR foydalanuvchi umumiy savol so'rayotgan, salomlashayotgan, imkoniyatlaringizni/qobiliyatlaringizni "
            "(masalan: 'qo'lingdan nima keladi', 'что ты умеешь', 'привет', 'salom', 'qaysi tillarni bilasan', 'какие языки поддерживаешь', 'status nima') so'rayotgan bo'lsa:\n"
            "   Unga to'liq, aqlli, samimiy va chiroyli javob yozing (foydalanuvchi tilida) va javobingiz oxirida AYNAN quyidagi JSON blokini qaytaring:\n"
            "```json\n"
            "{\n"
            '  "task_type": "conversational",\n'
            '  "direct_answer": "Foydalanuvchi tilida to\'liq, chiroyli va formatlangan javob matni..."\n'
            "}\n"
            "```\n\n"
            "3. AGAR foydalanuvchi SHU PLATFORMANING O'ZINI (barcha Python modullari, server.py, agent_engine.py, llm_client.py, models_hub.py, tools.py, kod bazasi, arxitektura) audit qilish, tahlil qilish, sekin qismlarni topish, xatolarni (try-catch) tekshirish yoki ortiqcha kodlarni tozalashni so'rayotgan bo'lsa:\n"
            "   DIQQAT: Yangi loyiha papkasi ochilmaydi! Mutaxassis platformaning asosiy katalogidagi fayllarni `list_dir` va `read_file` bilan o'qib, chuqur tahlil qiladi.\n"
            "```json\n"
            "{\n"
            '  "task_type": "platform_audit",\n'
            '  "specialist_role": "security_auditor",\n'
            '  "files": ["server.py", "agent_engine.py", "llm_client.py", "models_hub.py", "tools.py", "skill_matrix.py", "config.py"],\n'
            '  "steps": ["Platforma modullarini list_dir va read_file bilan o\'qish", "Arxitektura, xavfsizlik va sekin ishlash omillarini tahlil qilish", "Xatolarni qayta ishlash (try-catch) sifatini tekshirish", "Batafsil audit hisoboti va takliflar berish"],\n'
            '  "acceptance_criteria": ["Barcha Python modullari tahlil qilindi", "Konkret audit xulosasi berildi"]\n'
            "}\n"
            "```\n\n"
            "4. AGAR foydalanuvchi YANGI dasturiy/muhandislik loyihasi (kod yozish, sayt, bot, script, backend API, frontend, web sahifa) yaratishni so'rayotgan bo'lsa:\n"
            "   Vazifani tahlil qilib, qisqa reja yozing (foydalanuvchi tilida) va oxirida AYNAN quyidagi JSON blokini qaytaring:\n"
            "```json\n"
            "{\n"
            '  "task_type": "code_project",\n'
            '  "project_name": "qisqa_papka_nomi",\n'
            '  "specialist_role": "yuqoridagi ro\'yxatdan bitta mos id",\n'
            '  "files": ["yaratilishi kerak bo\'lgan fayllar yo\'llari"],\n'
            '  "steps": ["bajarilishi kerak bo\'lgan aniq qadamlar"],\n'
            '  "acceptance_criteria": ["ish tugadi deyish uchun tekshiriladigan shartlar"],\n'
            '  "verification_command": "natijani tekshiruvchi terminal buyrug\'i yoki bo\'sh satr"\n'
            "}\n"
            "```"
        )

        res = await llm_client.complete(
            pm_model,
            [{"role": "system", "content": pm_md}, {"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=3000, custom_keys=custom_keys
        )

        is_conv = is_conversational_query(task_prompt)
        lang = detect_query_lang(task_prompt)

        if not res["success"]:
            if is_conv:
                if lang == "ru":
                    default_answer = (
                        "Я — **Project Manager** и центральный оркестратор платформы **Ant Colony AI**.\n\n"
                        "### Мои основные возможности:\n"
                        "1. **Универсальная разработка:** Python (FastAPI, Django), Node.js (React, Vue, Express), Go, PHP (Laravel), Rust, HTML5/CSS3/JS анимации.\n"
                        "2. **12 специализированных ролей ИИ:** Архитектор, Frontend, Backend, UI/UX дизайнер, QA инженер тестирования, Аудитор безопасности, DevOps инженер, Аналитик данных.\n"
                        "3. **Автоматический контроль качества (QA и Безопасность):** Проверка синтаксиса, анализ структуры DOM и выявление уязвимостей с автоматическим исправлением ошибок.\n"
                        "4. **Автономное рабочее окружение:** Создание готовых проектов в папке `04_Loyihalar` на рабочем столе и запуск через встроенный терминал.\n\n"
                        "Поставьте любую задачу (например: *'Создать REST API авторизации на FastAPI'* или *'Интерактивный неоновый таймер на HTML/CSS/JS'*), и я организую команду ИИ-агентов для ее выполнения!"
                    )
                else:
                    default_answer = (
                        "Men **Ant Colony AI** universal agentlar platformasining Markaziy Project Manageriman.\n\n"
                        "### Asosiy imkoniyatlarim:\n"
                        "1. **Universal dasturlash:** Python (FastAPI/Django), Node.js (React/Vue/Express), Go, PHP (Laravel), Rust, HTML/CSS/JS animatsiyalar.\n"
                        "2. **12 ta ixtisoslashgan rol:** Arxitektor, Frontend, Backend, UI/UX, QA Test, Xavfsizlik auditi, DevOps, Ma'lumotlar tahlili.\n"
                        "3. **Avtomatik sifat tekshiruvi (QA & Security):** Kod sintaksisi, DOM bog'liqliklari va zaifliklarni deterministik tekshirish va xatolarni avtomatik tuzatish.\n"
                        "4. **Haqiqiy ishchi muhit:** Desktop `04_Loyihalar` katalogida mustaqil loyihalar yaratish va terminal asboblari orqali ishga tushirish.\n\n"
                        "Menga aniq topshiriq bering (masalan: *\"FastAPI da foydalanuvchilar ro'yxati API sini yoz\"* yoki *\"Neon kalkulyator veb ilovasi\"*), men mutaxassislarni ishga solib, to'liq tayyorlab beraman!"
                    )
                return {
                    "ok": True, "error": None,
                    "plan_text": default_answer, "reasoning": "Пользователь запросил возможности системы — предоставлен полный ответ.",
                    "model_used": pm_model,
                    "spec": {"task_type": "conversational", "direct_answer": default_answer, "specialist_role": default_role, "files": [], "steps": [], "acceptance_criteria": [], "verification_command": "", "project_name": None},
                    "usage": {},
                }

            return {
                "ok": False, "error": res.get("error", ""),
                "plan_text": "", "reasoning": "", "model_used": pm_model,
                "spec": {"task_type": "code_project", "specialist_role": default_role, "files": [], "steps": [],
                         "acceptance_criteria": [], "verification_command": "", "project_name": None},
                "usage": {},
            }

        inline_reasoning, text = split_reasoning(res["text"])
        reasoning = (res.get("reasoning") or "") + ("\n" + inline_reasoning if inline_reasoning else "")
        spec = extract_json_block(text) or {}

        # If user did not ask to create/write code, strictly force conversational task_type
        if is_conv:
            task_type = "conversational"
        else:
            task_type = spec.get("task_type") or "code_project"
        role = spec.get("specialist_role")
        valid_roles = {r["id"] for r in DEFAULT_ROLE_DEFINITIONS}
        if role not in valid_roles or role == "pm_orchestrator":
            role = default_role

        # JSON blokini odamga ko'rsatiladigan matndan olib tashlaymiz.
        plan_text = _JSON_BLOCK_RE.sub("", text).strip() or text.strip()

        return {
            "ok": True, "error": None,
            "plan_text": plan_text,
            "reasoning": reasoning.strip(),
            "model_used": res["model_used"],
            "usage": res.get("usage", {}),
            "spec": {
                "task_type": task_type,
                "direct_answer": spec.get("direct_answer") or plan_text,
                "project_name": spec.get("project_name"),
                "specialist_role": role,
                "files": spec.get("files") if isinstance(spec.get("files"), list) else [],
                "steps": spec.get("steps") if isinstance(spec.get("steps"), list) else [],
                "acceptance_criteria": spec.get("acceptance_criteria") if isinstance(spec.get("acceptance_criteria"), list) else [],
                "verification_command": spec.get("verification_command") or "",
            },
        }

    async def run_orchestrated_task_stream(
        self,
        task_prompt: str,
        custom_keys: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.time()
        # Orkestratsiya davomida fon pinglari to'xtaydi — bepul kvota agentlarga kerak.
        models_hub.mark_busy(600)

        try:
            async for event in self._orchestrate(task_prompt, custom_keys, start_time):
                yield sanitize_event(event)
        finally:
            models_hub.clear_busy()

    async def _orchestrate(
        self, task_prompt: str,
        custom_keys: Optional[Dict[str, str]],
        start_time: float,
    ) -> AsyncGenerator[Dict[str, Any], None]:

        heuristic_role = select_specialist_role(task_prompt)
        pm_model = skill_matrix.get_best_model_for_role("pm_orchestrator")
        pm_md = skill_matrix.get_role_md_content("pm_orchestrator.md")

        yield {
            "type": "workflow_phase", "phase_id": "requirements", "station": "pm",
            "title": "Сбор и анализ требований",
            "agent_name": f"Project Manager ({pm_model})", "status": "active",
        }
        yield {
            "type": "ceo_briefing", "progress_pct": 10,
            "phase_title": "Анализ требований",
            "active_agent": f"Project Manager ({pm_model})",
            "status_message": "PM анализирует задачу, формирует архитектурный план и назначает ведущую роль.",
            "bottleneck_alert": None, "eta_seconds": 50,
            "project_dir": str(PROJECTS_BASE_DIR),
        }

        # --- Phase 1: PM tuzilmali reja tuzadi (rolni ham o'zi tanlaydi) ---
        plan = await self._plan_with_pm(task_prompt, pm_model, pm_md, heuristic_role, custom_keys)
        spec = plan["spec"]

        # Agar foydalanuvchi umumiy savol so'ragan yoki suhbatlashayotgan bo'lsa:
        if spec.get("task_type") == "conversational":
            if plan["reasoning"]:
                yield {
                    "type": "reasoning", "station": "pm", "agent_name": "Project Manager",
                    "reasoning_text": plan["reasoning"][:4000],
                    "reasoning_tokens": plan["usage"].get("reasoning_tokens") or (len(plan["reasoning"].split()) * 4 // 3),
                }

            answer = spec.get("direct_answer") or plan["plan_text"] or "Я — Project Manager платформы Ant Colony AI. Готов к выполнению любых задач."
            # Strip raw JSON wraps if returned inside direct_answer
            if isinstance(answer, str) and (answer.strip().startswith('{') or '```json' in answer):
                m_json = re.search(r'\{[\s\S]*\}', answer)
                if m_json:
                    try:
                        p_obj = json.loads(m_json.group(0))
                        answer = p_obj.get("direct_answer") or p_obj.get("response") or p_obj.get("message") or _JSON_BLOCK_RE.sub("", answer).strip()
                    except Exception:
                        answer = _JSON_BLOCK_RE.sub("", answer).strip()
            yield {
                "type": "pm_plan_ready", "station": "pm",
                "plan_content": answer,
                "metrics": plan["usage"],
                "assigned_role": "pm_orchestrator", "assigned_model": pm_model,
                "project_dir": str(PROJECTS_BASE_DIR),
            }
            yield {
                "type": "workflow_phase", "phase_id": "monitoring", "station": "pm",
                "title": "Ответ сформирован",
                "agent_name": f"Project Manager ({pm_model})", "status": "completed",
            }
            yield {
                "type": "ceo_briefing", "progress_pct": 100,
                "phase_title": "Диалог завершен",
                "active_agent": f"Project Manager ({pm_model})",
                "status_message": "На вопрос пользователя дан подробный ответ.",
                "bottleneck_alert": None, "eta_seconds": 0,
                "project_dir": str(PROJECTS_BASE_DIR),
            }
            yield {
                "type": "orchestration_completed",
                "duration_seconds": round(time.time() - start_time, 2),
                "final_score": 100,
                "score_breakdown": {"qa": 100, "artifacts": 100, "execution": 100},
                "created_files": [],
                "eval_summary": {"summary": answer, "score": 100},
            }
            return

        coder_role_id = spec["specialist_role"]

        task_lower = task_prompt.lower()
        is_platform_audit = (
            spec.get("task_type") == "platform_audit"
            or any(kw in task_lower for kw in [
                "platforma", "platformani", "barcha python modullar", "modullarni to'liq audit",
                "modullarni audit", "server.py", "agent_engine.py", "llm_client.py",
                "o'zingni kodingni", "ozingni kodingni", "shu platforma", "o'zingni audit",
                "arxitekturani audit", "kod bazani tekshir"
            ])
        )

        if is_platform_audit:
            project_dir = BASE_DIR
            project_slug = "Ant Colony AI Platform (Asosiy kod bazasi)"
            set_active_project_dir(BASE_DIR)
        else:
            project_dir = allocate_project_dir(task_prompt, spec.get("project_name"))
            project_slug = project_dir.name
            set_active_project_dir(project_dir)

        coder_model = skill_matrix.get_best_model_for_role(coder_role_id)
        tester_model = skill_matrix.get_best_model_for_role("qa_test_automation")
        security_model = skill_matrix.get_best_model_for_role("security_auditor")

        role_def = next((r for r in DEFAULT_ROLE_DEFINITIONS if r["id"] == coder_role_id), None)
        coder_display = (role_def["name"] if role_def else coder_role_id.replace("_", " ").title())
        coder_md = skill_matrix.get_role_md_content(f"{coder_role_id}.md")
        tester_md = skill_matrix.get_role_md_content("qa_test_automation.md")
        security_md = skill_matrix.get_role_md_content("security_auditor.md")

        yield {
            "type": "orchestration_start", "task": task_prompt,
            "project_name": project_slug, "project_path": str(project_dir),
            "pm_model": plan["model_used"], "coder_role": coder_role_id,
            "coder_model": coder_model, "tester_model": tester_model,
            "security_model": security_model, "timestamp": time.time(),
        }

        if plan["reasoning"]:
            yield {
                "type": "reasoning", "station": "pm", "agent_name": "Project Manager",
                "reasoning_text": plan["reasoning"][:4000],
                "reasoning_tokens": plan["usage"].get("reasoning_tokens") or (len(plan["reasoning"].split()) * 4 // 3),
            }

        if not plan["ok"]:
            yield {
                "type": "agent_error", "station": "pm", "agent_name": "Project Manager",
                "error": plan["error"],
            }

        plan_display = plan["plan_text"] or "Требования к проекту проанализированы."
        if spec["files"] or spec["steps"]:
            plan_display += "\n\n**Файлы для создания:** " + (", ".join(f"`{f}`" for f in spec["files"]) or "—")
            if spec["acceptance_criteria"]:
                plan_display += "\n**Критерии приемки:**\n" + "\n".join(f"- {c}" for c in spec["acceptance_criteria"])

        yield {
            "type": "pm_plan_ready", "station": "pm",
            "plan_content": plan_display,
            "metrics": plan["usage"],
            "assigned_role": coder_role_id, "assigned_model": coder_model,
            "project_dir": str(project_dir),
        }

        # --- Phase 2: Mutaxassis agent asbob-qadam siklida ishlaydi ---
        yield {
            "type": "ceo_briefing", "progress_pct": 35,
            "phase_title": "Разработка кода и сохранение файлов" if not is_platform_audit else "Platforma modullarini audit qilish",
            "active_agent": f"{coder_display} ({coder_model})",
            "status_message": f"Mutaxassis {project_slug} uchun modullarni o'qib tahlil qilmoqda." if is_platform_audit else f"Mutaxassis {project_slug} loyihasi uchun fayllarni yozmoqda va tekshirmoqda.",
            "bottleneck_alert": None, "eta_seconds": 60, "project_dir": str(project_dir),
        }
        yield {
            "type": "workflow_phase", "phase_id": "coding", "station": "coder",
            "title": "Разработка кода и построение архитектуры" if not is_platform_audit else "Modullarni o'qish va chuqur audit qilish",
            "agent_name": f"{coder_display} ({coder_model})", "status": "active",
        }

        if is_platform_audit:
            coder_context = (
                f"Project Manager auditi rejasi:\n{plan['plan_text']}\n\n"
                f"DIQQAT: Siz Ant Colony AI platformasining asosiy katalogidasiz (`{BASE_DIR}`).\n"
                "Asosiy Python modullari: `server.py`, `agent_engine.py`, `llm_client.py`, `models_hub.py`, `tools.py`, `skill_matrix.py`, `prompt_cache.py`, `config.py`.\n"
                "VAZIFANGIZ: `list_dir` va `read_file` asboblari yordamida ushbu Python modullarini o'qing. Ulardagi xatolarni qayta ishlash (try-catch), sekin ishlayotgan funksiyalar, ortiqcha kodlar va xavfsizlik holatini chuqur tahlil qiling va foydalanuvchiga to'liq, professional hisobot taqdim eting!\n"
            )
        else:
            coder_context = (
                f"Project Manager rejasi:\n{plan['plan_text']}\n\n"
                + (f"Yaratilishi kerak bo'lgan fayllar: {', '.join(spec['files'])}\n" if spec["files"] else "")
                + (f"Qadamlar:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(spec["steps"])) + "\n" if spec["steps"] else "")
                + (f"Qabul shartlari:\n" + "\n".join(f"- {c}" for c in spec["acceptance_criteria"]) + "\n" if spec["acceptance_criteria"] else "")
            )

        coder_result: Optional[AgentRunResult] = None
        async for event in run_agent(
            station="coder", agent_name=coder_display, model_id=coder_model,
            role_md=coder_md, task=task_prompt, context=coder_context,
            tool_names=["write_file", "edit_file", "read_file", "list_dir",
                        "run_shell_command", "execute_python", "calculate"],
            temperature=0.2, max_tokens=8192, custom_keys=custom_keys,
        ):
            if event["type"] == "agent_done":
                coder_result = event["result"]
            yield event

        if coder_result is None:
            coder_result = AgentRunResult()
            coder_result.error = "Mutaxassis agent natija qaytarmadi"

        # --- Phase 3: QA va Xavfsizlik PARALLEL tekshiradi ---
        yield {
            "type": "ceo_briefing", "progress_pct": 65,
            "phase_title": "QA и аудит безопасности (параллельно)",
            "active_agent": f"QA ({tester_model}) + Security ({security_model})",
            "status_message": "Два аудитора параллельно инспектируют код и запускают тесты.",
            "bottleneck_alert": None, "eta_seconds": 35, "project_dir": str(project_dir),
        }
        yield {
            "type": "workflow_phase", "phase_id": "testing", "station": "tester",
            "title": "Тестирование кода и проверка безопасности",
            "agent_name": f"QA ({tester_model}) + Security ({security_model})", "status": "active",
        }

        review: Dict[str, str] = {}
        async for event in self._stream_reviews(
            out=review,
            task_prompt=task_prompt, project_dir=project_dir, spec=spec,
            files_written=coder_result.files_written,
            tester_model=tester_model, tester_md=tester_md,
            security_model=security_model, security_md=security_md,
            custom_keys=custom_keys,
        ):
            yield event

        qa_text = review.get("qa_text", "")
        security_text = review.get("security_text", "")
        qa_score = extract_score(qa_text)

        # Deterministik statik va sintaksis tahlili
        from tools import verify_code_syntax
        syntax_res = verify_code_syntax()
        if not syntax_res.get("success"):
            issues_list = syntax_res.get("issues", [])
            syntax_issues_text = "\n".join(
                f"- `{i.get('file')}` ({i.get('type')}): {i.get('message')}"
                for i in issues_list
            )
            qa_text = (qa_text + "\n\n### Aniqlangan sintaksis va tuzilish xatolari:\n" + syntax_issues_text).strip()
            # Xato bo'lsa QA bahosini pasaytiramiz, toki tuzatish sikli ishga tushsin
            qa_score = min(qa_score if qa_score is not None else 40.0, 45.0)

        yield {
            "type": "qa_verified", "station": "tester",
            "feedback": qa_text or "Отчет QA пуст.",
            "qa_score": qa_score, "model": tester_model,
        }
        yield {
            "type": "security_report", "station": "tester",
            "feedback": security_text or "Отчет безопасности пуст.",
            "model": security_model,
        }

        # --- Phase 4: Tuzatish (repair) sikli ---
        repair_rounds = 0
        repair_notes: List[str] = []
        threshold = AGENT_CONFIG["repair_threshold"]
        max_rounds = AGENT_CONFIG["max_repair_rounds"]

        while (
            repair_rounds < max_rounds
            and (
                (qa_score is not None and qa_score < threshold)
                or not coder_result.files_written
                or coder_result.error
            )
        ):
            repair_rounds += 1
            reason = (
                f"Оценка QA {qa_score}/100 (порог {threshold})" if qa_score is not None and qa_score < threshold
                else ("Файлы не были записаны" if not coder_result.files_written else "Агент завершился с ошибкой")
            )

            yield {
                "type": "workflow_phase", "phase_id": "coding", "station": "coder",
                "title": f"Цикл исправления #{repair_rounds}: устранение замечаний",
                "agent_name": f"{coder_display} ({coder_model})", "status": "active",
            }
            yield {
                "type": "repair_round_start", "station": "coder", "round": repair_rounds,
                "reason": reason,
                "message": f"Запущен цикл исправления #{repair_rounds} — {reason}",
            }
            yield {
                "type": "ceo_briefing", "progress_pct": 70 + repair_rounds * 5,
                "phase_title": f"Цикл исправления #{repair_rounds}",
                "active_agent": f"{coder_display} ({coder_model})",
                "status_message": f"{reason}. Специалист устраняет замечания.",
                "bottleneck_alert": reason, "eta_seconds": 30, "project_dir": str(project_dir),
            }

            repair_context = (
                f"Вы ранее работали над этим проектом. Каталог: `{project_dir}`\n"
                f"Записанные файлы: {', '.join(coder_result.files_written) or '(файлы еще не созданы)'}\n\n"
                f"## Отчет QA тестирования\n{qa_text[:4000]}\n\n"
                f"## Отчет безопасности\n{security_text[:2500]}\n\n"
                "Устраните указанные ЗАМЕЧАНИЯ. Сначала прочитайте существующий код через `read_file`, "
                "затем внесите точечные исправления через `edit_file` или `write_file`, "
                "и проверьте результат. Не создавайте проект с нуля."
            )

            repair_result: Optional[AgentRunResult] = None
            async for event in run_agent(
                station="coder", agent_name=f"{coder_display} (tuzatish #{repair_rounds})",
                model_id=coder_model, role_md=coder_md,
                task=f"Устранение замечаний: {task_prompt}",
                context=repair_context,
                tool_names=["read_file", "list_dir", "edit_file", "write_file",
                            "run_shell_command", "execute_python"],
                max_steps=max(4, AGENT_CONFIG["max_tool_steps"] // 2),
                temperature=0.15, max_tokens=8192, custom_keys=custom_keys,
            ):
                if event["type"] == "agent_done":
                    repair_result = event["result"]
                yield event

            if repair_result:
                # Natijalarni birlashtiramiz — umumiy signal to'liq bo'lishi kerak.
                for f in repair_result.files_written:
                    if f not in coder_result.files_written:
                        coder_result.files_written.append(f)
                coder_result.tool_calls += repair_result.tool_calls
                coder_result.tool_failures += repair_result.tool_failures
                coder_result.steps += repair_result.steps
                for key in coder_result.usage:
                    coder_result.usage[key] += repair_result.usage.get(key, 0)
                coder_result.final_text = repair_result.final_text or coder_result.final_text
                coder_result.error = repair_result.error
                repair_notes.append(f"Sikl #{repair_rounds}: {(repair_result.final_text or '')[:300]}")

            # QA qayta tekshiradi (xavfsizlik auditi qayta yurgizilmaydi — kvota tejash).
            recheck: Dict[str, str] = {}
            async for event in self._stream_reviews(
                out=recheck,
                task_prompt=task_prompt, project_dir=project_dir, spec=spec,
                files_written=coder_result.files_written,
                tester_model=tester_model, tester_md=tester_md,
                security_model=security_model, security_md=security_md,
                custom_keys=custom_keys, security_enabled=False,
            ):
                yield event

            new_qa_text = recheck.get("qa_text", "")
            new_score = extract_score(new_qa_text)
            if new_qa_text:
                qa_text = new_qa_text
            if new_score is not None:
                qa_score = new_score

            yield {
                "type": "qa_verified", "station": "tester",
                "feedback": qa_text, "qa_score": qa_score,
                "model": tester_model, "repair_round": repair_rounds,
            }

        # --- Phase 5: Haqiqiy signallarga asoslangan baholash ---
        eval_input = skill_matrix.score_from_signals(
            qa_score=qa_score,
            files_written=len(coder_result.files_written),
            tool_calls=coder_result.tool_calls,
            tool_failures=coder_result.tool_failures,
            hit_step_limit=coder_result.hit_step_limit,
            had_error=bool(coder_result.error),
        )
        evaluated_score = eval_input["score"]

        coder_eval = skill_matrix.record_evaluation(
            role_id=coder_role_id, model_id=coder_model, score=evaluated_score,
            feedback=(qa_text or "")[:200],
        )

        # QA modelining bahosi: hisobotining foydaliligiga qarab (avval qat'iy 95 edi).
        qa_useful = bool(qa_text) and len(qa_text) > 120
        qa_gave_score = qa_score is not None
        qa_self_score = 60.0 + (20.0 if qa_useful else 0.0) + (20.0 if qa_gave_score else 0.0)
        qa_eval = skill_matrix.record_evaluation(
            role_id="qa_test_automation", model_id=tester_model, score=qa_self_score,
            feedback="Оценка на основе полноты отчета и покрытия тестами",
        )

        yield {
            "type": "role_evaluation",
            "coder_eval": coder_eval, "qa_eval": qa_eval,
            "coder_role": coder_role_id, "coder_model": coder_model,
            "score": evaluated_score, "score_breakdown": eval_input["breakdown"],
            "agent_metrics": coder_result.as_dict(),
            "message": (f"Оценка: {coder_model} -> {coder_role_id}: {evaluated_score}/100 "
                        f"(QA: {qa_score if qa_score is not None else '—'}, "
                        f"файлов: {len(coder_result.files_written)}, "
                        f"успешность инструментов: {round(coder_result.tool_success_rate * 100)}%)"),
        }

        # --- Phase 6: Yakun ---
        yield {
            "type": "workflow_phase", "phase_id": "deploy", "station": "deployer",
            "title": "Сборка и упаковка артефактов", "agent_name": "DevOps Agent", "status": "active",
        }

        tree = list_dir()
        created_files = [e["path"] for e in tree.get("entries", []) if e["type"] == "file"]

        yield {
            "type": "workflow_phase", "phase_id": "completed", "station": "pm",
            "title": "Задача завершена, результаты сохранены",
            "agent_name": "Project Manager", "status": "completed",
        }
        yield {
            "type": "ceo_briefing", "progress_pct": 100,
            "phase_title": "Проект успешно завершен",
            "active_agent": "Приемка результатов (CEO)",
            "status_message": (f"{len(created_files)} fayl {project_dir} manzilida. "
                               f"Yakuniy baho: {evaluated_score}/100."),
            "bottleneck_alert": None, "eta_seconds": 0, "project_dir": str(project_dir),
        }

        models_hub.record_task_completed()

        files_block = "\n".join(f"- `{f}`" for f in created_files) or "- (файлы не были созданы)"
        coder_summary = coder_result.final_text or "(xulosa yo'q)"
        total_tokens = coder_result.usage["prompt_tokens"] + coder_result.usage["completion_tokens"]
        repair_block = ("\n\n**Tuzatish sikllari:** " + str(repair_rounds) + "\n"
                        + "\n".join(f"- {n}" for n in repair_notes)) if repair_rounds else ""

        final_summary = (
            f"### Задача успешно выполнена\n\n"
            f"**Loyiha manzili:** `{project_dir}`\n\n"
            f"**PM rejasi (`{plan['model_used']}`):**\n{plan['plan_text']}\n\n"
            f"---\n\n**Yaratilgan fayllar ({len(created_files)}):**\n{files_block}\n\n"
            f"---\n\n**Mutaxassis xulosasi (`{coder_role_id}` • `{coder_model}`):**\n"
            f"{coder_summary}\n\n"
            f"*Ish ko'rsatkichlari: {coder_result.steps} qadam, {coder_result.tool_calls} asbob chaqirig'i, "
            f"{round(coder_result.tool_success_rate * 100)}% muvaffaqiyat, {total_tokens} token.*\n\n"
            f"---\n\n**Отчет QA (`{tester_model}`):**\n{qa_text or '—'}\n\n"
            f"---\n\n**Xavfsizlik auditi (`{security_model}`):**\n{security_text or '—'}"
            f"{repair_block}\n\n"
            f"---\n\n**Baholash (Continuous Learning):**\n"
            f"- Yakuniy ball: **{evaluated_score}/100** "
            f"(QA: {eval_input['breakdown'].get('qa')} • natija: {eval_input['breakdown'].get('artifacts')} "
            f"• bajarilish: {eval_input['breakdown'].get('execution')})\n"
            f"- `{coder_model}` -> `{coder_role_id}` yangi reytingi: **{coder_eval.get('new_category_score')}/100**\n"
            f"- Keyingi vazifalar uchun yetakchi: `{coder_eval.get('assigned_leader')}`"
        )

        yield {
            "type": "orchestration_completed",
            "final_content": final_summary,
            "eval_summary": coder_eval,
            "project_dir": str(project_dir),
            "project_slug": project_slug,
            "created_files": created_files,
            "plan": plan,
            "coder_role": coder_role_id,
            "coder_model": coder_model,
            "coder_summary": coder_summary,
            "tester_model": tester_model,
            "qa_score": qa_score,
            "qa_text": qa_text,
            "security_model": security_model,
            "security_text": security_text,
            "final_score": evaluated_score,
            "score_breakdown": eval_input["breakdown"],
            "repair_rounds": repair_rounds,
            "repair_notes": repair_notes,
            "agent_metrics": coder_result.as_dict(),
            "total_duration_sec": round(time.time() - start_time, 2),
        }

    async def _stream_reviews(
        self, *, out: Dict[str, str], task_prompt: str, project_dir: Path,
        spec: Dict[str, Any], files_written: List[str],
        tester_model: str, tester_md: str,
        security_model: str, security_md: str,
        custom_keys: Optional[Dict[str, str]], security_enabled: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        QA va xavfsizlik auditini PARALLEL yugurtiradi va hodisalarni DARHOL uzatadi.

        Muhim farq: ikkala auditor ham HAQIQIY asboblarga ega — fayllarni o'qiydi
        va testlarni yurgizadi. Ilgari QA agentiga dasturchi javobining faqat
        1500 belgisi matn sifatida berilardi, ya'ni u haqiqiy kodni ko'rmasdi.

        Natijalar `out` lug'atiga yoziladi: `out["qa_text"]`, `out["security_text"]`.
        """
        criteria = "\n".join(f"- {c}" for c in spec.get("acceptance_criteria", [])) or "- (aniq shart berilmagan)"
        files_hint = ", ".join(files_written) or "(dasturchi fayl yozmagan)"
        verify_cmd = spec.get("verification_command") or ""

        qa_task = (
            f"Topshiriq / Задача: \"{task_prompt}\"\n"
            f"Loyiha papkasi / Папка проекта: `{project_dir}`\n"
            f"Dasturchi yozgan fayllar / Файлы: {files_hint}\n\n"
            f"Qabul shartlari / Критерии приемки:\n{criteria}\n\n"
            + (f"Tavsiya etilgan tekshiruv buyrug'i: `{verify_cmd}`\n\n" if verify_cmd else "")
            + "Vazifangiz / Требования:\n"
            "1. MUHIM: Hisobotingizni foydalanuvchi topshirig'i yozilgan tilda yozing (Если запрос на русском — пишите на русском. If in English — write in English. O'zbekcha bo'lsa — o'zbek tilida yozing).\n"
            "2. `list_dir` bilan papka tarkibini ko'ring.\n"
            "3. `read_file` bilan har bir asosiy faylni O'QING — kodlarni to'liq tekshiring.\n"
            "4. Topilgan kamchiliklarni ANIQ ko'rsating: fayl nomi, qator, muammo, tuzatish yo'li.\n"
            "5. Yakunda albatta `Baho: NN/100` yoki `Оценка: NN/100` formatida ball qo'ying (masalan: `Baho: 92/100` yoki `Оценка: 92/100`).\n\n"
            "Ball mezoni: 90+ — to'liq ishlaydi; 70-89 — kichik kamchiliklar; 50-69 — jiddiy kamchiliklar; 50 dan past — ishlamaydi."
        )

        security_task = (
            f"Topshiriq / Задача: \"{task_prompt}\"\n"
            f"Loyiha papkasi / Папка проекта: `{project_dir}`\n"
            f"Fayllar: {files_hint}\n\n"
            "Vazifangiz / Требования:\n"
            "1. MUHIM: Hisobotingizni foydalanuvchi topshirig'i tilida yozing (ruscha, o'zbekcha yoki inglizcha).\n"
            "2. Kodni xavfsizlik nuqtai nazaridan tekshiring: `list_dir` va `read_file` bilan fayllarni o'qing. "
            "Quyidagilarga e'tibor bering: kodda qoldirilgan maxfiy kalitlar, SQL/shell/HTML inyeksiya imkoniyatlari, "
            "tekshirilmagan foydalanuvchi kirishi, xavfli fayl yo'llari, yetishmayotgan xato ishlovi.\n"
            "3. Har bir topilma uchun: fayl, muammo, xavflilik darajasi (kritik/yuqori/o'rta/past) va tuzatish yo'li. Muammo topilmasa, buni ochiq ayting."
        )

        qa_result: Dict[str, Any] = {"text": ""}
        sec_result: Dict[str, Any] = {"text": ""}

        streams = [
            self._capture_agent(
                station="tester", agent_name="QA Specialist", model_id=tester_model,
                role_md=tester_md, task=qa_task,
                tool_names=["list_dir", "read_file", "execute_python", "run_shell_command"],
                max_steps=6, temperature=0.1, sink=qa_result, custom_keys=custom_keys,
            )
        ]
        if security_enabled:
            streams.append(
                self._capture_agent(
                    station="tester", agent_name="Security Auditor", model_id=security_model,
                    role_md=security_md, task=security_task,
                    tool_names=["list_dir", "read_file"],
                    max_steps=5, temperature=0.1, sink=sec_result, custom_keys=custom_keys,
                )
            )

        try:
            async for event in merge_event_streams(streams):
                yield sanitize_event(event)
        finally:
            out["qa_text"] = qa_result.get("text", "") or ""
            out["security_text"] = sec_result.get("text", "") or ""

    async def _capture_agent(
        self, *, station: str, agent_name: str, model_id: str, role_md: str,
        task: str, tool_names: List[str], max_steps: int, temperature: float,
        sink: Dict[str, Any], custom_keys: Optional[Dict[str, str]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Agentni yugurtirib, yakuniy matnini `sink` ga yozadi va hodisalarni uzatadi."""
        async for event in run_agent(
            station=station, agent_name=agent_name, model_id=model_id,
            role_md=role_md, task=task, tool_names=tool_names,
            max_steps=max_steps, temperature=temperature,
            max_tokens=4096, custom_keys=custom_keys,
        ):
            if event["type"] == "agent_done":
                result: AgentRunResult = event["result"]
                sink["text"] = result.final_text
                sink["metrics"] = result.as_dict()
            yield event


agent_engine = AgentEngine()
