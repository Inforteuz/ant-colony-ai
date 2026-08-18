"""
Verification Test for AI Agent Platform.

Ikki qismdan iborat:
  * OFFLINE testlar — tarmoq va API kalitisiz ishlaydi. Asboblar, tool-call
    parseri, provayder xabar konvertorlari, model tanlash va baholash mantiqi.
  * ONLINE testlar — `--online` bayrog'i bilan ishga tushiriladi, haqiqiy API
    chaqiruvlarini talab qiladi.

Ishga tushirish:
    python3 test_platform.py            # faqat offline (tez, kvota sarflamaydi)
    python3 test_platform.py --online   # + haqiqiy model chaqiruvlari
"""
import sys
import json
import asyncio
import tempfile
from pathlib import Path

# Skript sifatida ishga tushirilganda ham paket topilsin
# (`python tests/test_platform.py`). pytest'da bu allaqachon ishlaydi.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ant_colony.config import MODELS_CATALOG, AGENT_CONFIG
from ant_colony.runtime.tools import (
    write_file, read_file, edit_file, list_files, list_dir, execute_python,
    calculate, run_shell_command, execute_tool, get_tool_schemas,
    render_tool_guide, set_active_project_dir, AVAILABLE_TOOLS,
)
from ant_colony.core.agent_loop import parse_text_tool_calls, split_reasoning
from ant_colony.llm.client import _to_openai_messages, _to_gemini_payload, build_fallback_chain
from ant_colony.core.agent_engine import (
    sanitize_slug, select_specialist_role, extract_json_block, extract_score,
)
from ant_colony.core.skill_matrix import skill_matrix
from ant_colony.llm.models_hub import models_hub
from ant_colony.llm.prompt_cache import prompt_cache

PASSED = 0
FAILED = []


def check(name: str, condition: bool, detail: str = ""):
    global PASSED
    if condition:
        PASSED += 1
        print(f"  ✓ {name}")
    else:
        FAILED.append(f"{name} — {detail}")
        print(f"  ✗ {name}  {detail}")


# ---------------------------------------------------------------- OFFLINE

def test_tools():
    print("\n=== 1. Asboblar (fayl tizimi, papkalar, xavfsizlik) ===")
    with tempfile.TemporaryDirectory() as tmp:
        set_active_project_dir(Path(tmp))

        r = write_file("index.html", "<h1>Salom</h1>")
        check("write_file ildizga yozadi", r["success"] and Path(tmp, "index.html").exists())

        # Eng muhim tuzatish: papka ichidagi yo'llar
        r = write_file("src/utils/helpers.py", "def add(a, b):\n    return a + b\n")
        check("write_file papka ichiga yozadi (src/utils/...)",
              r["success"] and Path(tmp, "src/utils/helpers.py").exists(),
              f"got path={r.get('path')}")
        check("write_file to'g'ri nisbiy yo'lni qaytaradi",
              r.get("filename") == "src/utils/helpers.py", f"got {r.get('filename')}")
        check("write_file Python sintaksisini tekshiradi",
              "to'g'ri" in (r.get("syntax_check") or ""), str(r.get("syntax_check")))

        r = write_file("bad.py", "def broken(:\n")
        check("write_file buzuq sintaksis haqida ogohlantiradi",
              "SyntaxError" in (r.get("syntax_check") or ""))

        # Yo'ldan chiqishga urinish loyiha papkasida qolishi kerak
        r = write_file("../../../tmp/evil_escape.txt", "x")
        check("write_file yo'ldan chiqishni bloklaydi",
              r["success"] and Path(r["path"]).resolve().is_relative_to(Path(tmp).resolve()),
              f"path={r.get('path')}")

        r = read_file("src/utils/helpers.py")
        check("read_file papka ichidan o'qiydi", r["success"] and "def add" in r["content"])

        r = edit_file("src/utils/helpers.py", "a + b", "a + b + 0")
        check("edit_file matnni almashtiradi", r["success"])
        check("edit_file natijasi diskda", "a + b + 0" in Path(tmp, "src/utils/helpers.py").read_text())

        r = edit_file("src/utils/helpers.py", "YO'Q_MATN", "x")
        check("edit_file topilmagan matnda tushunarli xato beradi",
              not r["success"] and "topilmadi" in r["error"])

        r = list_dir()
        paths = {e["path"] for e in r["entries"]}
        check("list_dir papka ichidagi fayllarni ko'radi", "src/utils/helpers.py" in paths, str(paths))

        r = list_files()
        names = {f["name"] for f in r["files"]}
        check("list_files papka yo'llarini saqlaydi", "src/utils/helpers.py" in names, str(names))

        r = execute_python("print(sum(i*i for i in range(1, 11)))")
        check("execute_python ishlaydi", r["success"] and r["stdout"].strip() == "385", str(r))

        r = execute_python("def x(:\n  pass")
        check("execute_python sintaksisni oldindan tekshiradi",
              not r["success"] and "SyntaxError" in r["stderr"])

        r = calculate("sqrt(144) + 3**2")
        check("calculate ishlaydi", r["success"] and r["result"] == 21.0, str(r))

        r = calculate("__import__('os').system('echo hack')")
        check("calculate xavfli kodni bloklaydi", not r["success"])

        r = run_shell_command("echo hello")
        check("run_shell_command ishlaydi", r["success"] and "hello" in r["stdout"])

        r = run_shell_command("rm -rf /")
        check("run_shell_command halokatli buyruqni bloklaydi",
              not r["success"] and r.get("blocked") is True, str(r))


def test_tool_dispatch():
    print("\n=== 2. Asbob dispatcher va sxemalar ===")
    schemas = get_tool_schemas()
    check("har bir asbobda sxema bor", len(schemas) == len(AVAILABLE_TOOLS))
    check("sxemalar JSON'ga aylanadi (func kaliti yo'q)",
          "func" not in json.dumps(schemas))
    for s in schemas:
        check(f"`{s['name']}` sxemasi to'g'ri",
              s["parameters"].get("type") == "object" and "properties" in s["parameters"])

    r = execute_tool("yoq_bunday_asbob", {})
    check("noma'lum asbob tushunarli xato beradi", not r["success"] and "yo'q" in r["error"])

    r = execute_tool("write_file", {"filename": "x.txt"})
    check("yetishmayotgan argument aniqlanadi",
          not r["success"] and "content" in r["error"], str(r))

    with tempfile.TemporaryDirectory() as tmp:
        set_active_project_dir(Path(tmp))
        r = execute_tool("write_file", {"filename": "a.txt", "content": "hi", "qoshimcha": 1})
        check("keraksiz argument filtrlanadi (TypeError bo'lmaydi)", r["success"], str(r))

    guide = render_tool_guide()
    check("tool guide barcha asboblarni sanaydi",
          all(f"`{n}`" in guide for n in AVAILABLE_TOOLS))
    check("tool guide chaqirish formatini ko'rsatadi", "```tool_call" in guide)


def test_tool_call_parsing():
    print("\n=== 3. Matndan tool-call ajratish (native calling zaxirasi) ===")
    text = (
        "Faylni yozaman.\n"
        '```tool_call\n{"tool": "write_file", "params": {"filename": "a.py", "content": "print(1)"}}\n```\n'
        "Keyin ishga tushiraman.\n"
        '```json\n{"tool": "execute_python", "params": {"code": "print(2)"}}\n```\n'
    )
    calls, clean = parse_text_tool_calls(text)
    check("bir xabardan bir NECHTA chaqiruv ajratiladi", len(calls) == 2, f"got {len(calls)}")
    check("birinchi chaqiruv to'g'ri", calls[0]["name"] == "write_file" and calls[0]["arguments"]["filename"] == "a.py")
    check("ikkinchi chaqiruv to'g'ri", calls[1]["name"] == "execute_python")
    check("bloklar matndan olib tashlanadi", "tool_call" not in clean and "Keyin ishga tushiraman" in clean)

    # Yassi (flat) format — ba'zi modellar shunday qaytaradi
    flat = '```tool_call\n{"tool": "read_file", "filename": "b.py"}\n```'
    calls, _ = parse_text_tool_calls(flat)
    check("yassi argument formati qo'llanadi",
          len(calls) == 1 and calls[0]["arguments"].get("filename") == "b.py", str(calls))

    # Mavjud bo'lmagan asbob e'tiborga olinmaydi
    calls, _ = parse_text_tool_calls('```tool_call\n{"tool": "hack_system", "params": {}}\n```')
    check("mavjud bo'lmagan asbob rad etiladi", len(calls) == 0)

    # Buzuq JSON dasturni yiqitmasligi kerak
    calls, _ = parse_text_tool_calls('```tool_call\n{"tool": "write_file", broken\n```')
    check("buzuq JSON xavfsiz o'tkazib yuboriladi", len(calls) == 0)

    reasoning, clean = split_reasoning("<think>ichki fikr</think>Yakuniy javob")
    check("<think> bloki ajratiladi", reasoning == "ichki fikr" and clean == "Yakuniy javob")


def test_message_conversion():
    print("\n=== 4. Provayderlar o'rtasida xabar konvertatsiyasi ===")
    canonical = [
        {"role": "system", "content": "Siz agentsiz"},
        {"role": "user", "content": "Fayl yoz"},
        {"role": "assistant", "content": "Yozaman",
         "tool_calls": [{"id": "c1", "name": "write_file", "arguments": {"filename": "a.py", "content": "x"}}]},
        {"role": "tool", "tool_call_id": "c1", "name": "write_file", "content": '{"success": true}'},
    ]

    oa = _to_openai_messages(canonical)
    check("OpenAI: system saqlanadi", oa[0]["role"] == "system")
    check("OpenAI: tool_calls to'g'ri shaklda",
          oa[2]["tool_calls"][0]["function"]["name"] == "write_file")
    check("OpenAI: arguments JSON satr",
          isinstance(oa[2]["tool_calls"][0]["function"]["arguments"], str))
    check("OpenAI: tool javobi id bilan bog'lanadi", oa[3]["tool_call_id"] == "c1")

    contents, system_text = _to_gemini_payload(canonical)
    check("Gemini: systemInstruction ajratiladi", system_text == "Siz agentsiz")
    check("Gemini: system `contents` ichiga tushmaydi",
          all("Siz agentsiz" not in json.dumps(c) for c in contents))
    flat = json.dumps(contents)
    check("Gemini: functionCall yasaladi", "functionCall" in flat)
    check("Gemini: functionResponse yasaladi", "functionResponse" in flat)
    check("Gemini: rollar faqat user/model", all(c["role"] in ("user", "model") for c in contents))

    # Ketma-ket bir xil rollar birlashtirilishi kerak
    contents, _ = _to_gemini_payload([
        {"role": "user", "content": "a"}, {"role": "user", "content": "b"}
    ])
    check("Gemini: ketma-ket bir xil rollar birlashadi", len(contents) == 1 and len(contents[0]["parts"]) == 2)


def test_fallback_chain():
    print("\n=== 5. Sog'liqqa asoslangan zaxira zanjiri ===")
    primary = "posiden/deepseek-v4-flash"
    dead = "gemini-3.7-flash"
    saved = dict(models_hub.stats[dead])
    try:
        models_hub.stats[dead]["status"] = "error"
        chain = build_fallback_chain(primary)
        check("zanjir asosiy modeldan boshlanadi", chain[0] == primary, str(chain[:2]))
        check("ishlamayotgan model zanjirdan chiqariladi", dead not in chain, str(chain))
        check("zanjir cheklangan uzunlikda", 1 < len(chain) <= 4, str(len(chain)))
        check("zanjirda takror yo'q", len(chain) == len(set(chain)))
    finally:
        models_hub.stats[dead].update(saved)


def test_model_selection():
    print("\n=== 6. Model tanlash: sog'liq + izlanish ===")
    role = "backend_engineer"
    chosen = skill_matrix.get_best_model_for_role(role, explore=False)
    check("rol uchun model tanlanadi", chosen in skill_matrix.matrix["models"], chosen)
    check("tanlov diskka yozilgan holatda saqlanadi",
          skill_matrix.matrix["role_assignments"][role] == chosen)

    # Ishlamayotgan modellar chetlatilishi kerak
    originals = {k: dict(v) for k, v in models_hub.stats.items()}
    try:
        for m_id in models_hub.stats:
            if m_id != "posiden/hy3":
                models_hub.stats[m_id]["status"] = "rate_limited"
        models_hub.stats["posiden/hy3"]["status"] = "online"
        picked = skill_matrix.get_best_model_for_role(role, explore=False)
        check("faqat sog'lom model tanlanadi", picked == "posiden/hy3", picked)
    finally:
        for k, v in originals.items():
            models_hub.stats[k].update(v)

    # Izlanish: 40 urinishda kamida ikki xil model chiqishi kerak
    picks = {skill_matrix.get_best_model_for_role(role, explore=True) for _ in range(40)}
    check("izlanish bir nechta modelni sinaydi (greedy qotib qolmaydi)",
          len(picks) > 1, f"picks={picks}, epsilon={AGENT_CONFIG['exploration_rate']}")


def test_scoring():
    print("\n=== 7. Signal asosidagi baholash ===")
    good = skill_matrix.score_from_signals(qa_score=95, files_written=3, tool_calls=6, tool_failures=0)
    bad = skill_matrix.score_from_signals(qa_score=95, files_written=0, tool_calls=0, tool_failures=0)
    check("fayl yozgan agent yuqori ball oladi", good["score"] >= 90, str(good))
    check("fayl yozmagan agent QA 95 bergan bo'lsa ham past ball oladi",
          bad["score"] < 75, str(bad))
    check("baho tarkibi ko'rinadi", set(good["breakdown"]) == {"qa", "artifacts", "execution"})

    failing = skill_matrix.score_from_signals(qa_score=90, files_written=2, tool_calls=10, tool_failures=8)
    check("asbob xatolari ballni pasaytiradi", failing["score"] < good["score"], str(failing))

    errored = skill_matrix.score_from_signals(qa_score=None, files_written=0, tool_calls=0, had_error=True)
    check("xatolik bilan tugagan ish eng past ballga tushadi", errored["score"] <= 55, str(errored))

    limited = skill_matrix.score_from_signals(qa_score=85, files_written=2, tool_calls=5,
                                             tool_failures=0, hit_step_limit=True)
    normal = skill_matrix.score_from_signals(qa_score=85, files_written=2, tool_calls=5, tool_failures=0)
    check("qadam limitiga urilish jarima olib keladi", limited["score"] < normal["score"])


def test_orchestration_helpers():
    print("\n=== 8. Orkestratsiya yordamchilari ===")
    check("slug tozalanadi va stopword tashlanadi",
          sanitize_slug("Menga kalkulyator uchun HTML sahifa yasab ber") == "kalkulyator_html_sahifa",
          sanitize_slug("Menga kalkulyator uchun HTML sahifa yasab ber"))
    check("bo'sh matndan ham slug chiqadi", len(sanitize_slug("!!!")) > 0)

    check("frontend vazifasi frontend rolga ketadi",
          select_specialist_role("HTML va CSS bilan responsive landing sahifa") == "frontend_architect")
    check("backend vazifasi backend rolga ketadi",
          select_specialist_role("FastAPI REST API endpoint yoz") == "backend_engineer")
    check("baza vazifasi database rolga ketadi",
          select_specialist_role("PostgreSQL schema va migration tayyorla") == "database_architect")
    check("algoritm vazifasi algorithm rolga ketadi",
          select_specialist_role("Graf algoritmi murakkabligini optimallashtir") == "algorithm_solver")
    check("noma'lum vazifa uchun zaxira rol bor",
          select_specialist_role("qwerty zxcvb") == "backend_engineer")

    spec = extract_json_block('Reja...\n```json\n{"specialist_role": "ui_designer", "files": ["a.css"]}\n```')
    check("PM JSON rejasi ajratiladi", spec and spec["specialist_role"] == "ui_designer", str(spec))
    check("JSON bo'lmasa None qaytadi", extract_json_block("oddiy matn") is None)

    check("QA balli ajratiladi", extract_score("Yaxshi ish.\nBaho: 87/100") == 87.0)
    check("Score formati ham ajratiladi", extract_score("Score: 42") == 42.0)
    check("ball topilmasa default qaytadi", extract_score("ballsiz matn", default=None) is None)


def test_cache():
    print("\n=== 9. Prompt kesh ===")
    msgs = [{"role": "user", "content": "test-cache-key"}]
    prompt_cache.set("m1", msgs, {"text": "javob"}, tokens_saved=100)
    hit = prompt_cache.get("m1", msgs)
    check("kesh saqlaydi va qaytaradi", hit and hit["response"]["text"] == "javob")
    check("boshqa xabarda kesh tegmaydi", prompt_cache.get("m1", [{"role": "user", "content": "boshqa"}]) is None)

    stats = prompt_cache.get_stats()
    check("kesh statistikasi to'liq",
          {"total_cached_entries", "hit_rate_pct", "max_entries", "evictions"} <= set(stats))
    check("kesh o'lchami cheklangan", stats["total_cached_entries"] <= stats["max_entries"])


def test_monitor_config():
    print("\n=== 10. Kvota tejash sozlamalari ===")
    check("fon monitoringi oralig'i uzoq (kvota tejaydi)",
          AGENT_CONFIG["health_monitor_interval_s"] >= 300,
          str(AGENT_CONFIG["health_monitor_interval_s"]))
    check("bir raundda hamma model urilmaydi",
          AGENT_CONFIG["health_monitor_batch"] < len(MODELS_CATALOG))
    check("tekshirilmagan model 'online' deb ko'rsatilmaydi",
          all(s["status"] != "online" or s["total_checks"] > 0 for s in models_hub.stats.values()))

    models_hub.mark_busy(60)
    check("orkestratsiya vaqtida monitoring to'xtaydi", models_hub.busy_until > 0)
    models_hub.clear_busy()
    check("orkestratsiyadan keyin monitoring tiklanadi", models_hub.busy_until == 0)


# ---------------------------------------------------------------- ONLINE

async def run_online_checks():
    """
    Haqiqiy provayder chaqiruvlari bilan tekshiruv.

    Nomi ataylab `test_` bilan boshlanmaydi: pytest uni avtomatik yig'ib olmasin.
    Ilgari u `test_online` edi va har `pytest` chaqiruvida "async def not natively
    supported" bilan yiqilardi hamda kvota sarflardi.
    Ishga tushirish: `python tests/test_platform.py --online`
    """
    print("\n=== ONLINE: haqiqiy model chaqiruvlari ===")
    from ant_colony.llm.client import llm_client

    res = await llm_client.complete(
        "posiden/deepseek-v4-flash",
        [{"role": "user", "content": "Faqat `PONG` deb javob ber."}],
        temperature=0.0, max_tokens=20,
    )
    check("LLM chaqiruvi ishlaydi", res["success"], res.get("error", ""))
    if res["success"]:
        print(f"     model={res['model_used']} provider={res['provider']} "
              f"{res['duration_ms']}ms fallback={res['fallback_used']}")

    with tempfile.TemporaryDirectory() as tmp:
        set_active_project_dir(Path(tmp))
        res = await llm_client.complete(
            "posiden/deepseek-v4-flash",
            [{"role": "user", "content": "`hello.txt` nomli faylga `salom` yozing."}],
            tools=get_tool_schemas(["write_file"]),
            temperature=0.0, max_tokens=500,
        )
        check("native function-calling javob qaytaradi", res["success"], res.get("error", ""))
        if res["success"]:
            print(f"     tool_calls={[c['name'] for c in res['tool_calls']]}")

    print("\n--- Agentic loop (haqiqiy fayl yaratish) ---")
    from ant_colony.core.agent_loop import run_agent
    with tempfile.TemporaryDirectory() as tmp:
        set_active_project_dir(Path(tmp))
        final = None
        async for ev in run_agent(
            station="coder", agent_name="Test Coder",
            model_id=skill_matrix.get_best_model_for_role("backend_engineer", explore=False),
            role_md=skill_matrix.get_role_md_content("backend_engineer.md"),
            task="`squares.py` fayl yarating: 1 dan 10 gacha sonlar kvadratlari yig'indisini chop etsin. Keyin ishga tushirib tekshiring.",
            tool_names=["write_file", "read_file", "execute_python"],
            max_steps=5, temperature=0.1, max_tokens=2000,
        ):
            if ev["type"] == "station_action":
                print(f"     [{ev['action_type']}] {ev['tool']}"
                      + (f" ok={ev.get('success')}" if ev["action_type"] == "tool_result" else ""))
            elif ev["type"] == "agent_done":
                final = ev["result"]

        check("agent asbob chaqirdi", final and final.tool_calls > 0,
              f"tool_calls={final.tool_calls if final else 'None'}")
        check("agent haqiqiy fayl yozdi", final and final.produced_artifacts,
              f"files={final.files_written if final else 'None'}")
        if final:
            print(f"     qadam={final.steps} asbob={final.tool_calls} "
                  f"xato={final.tool_failures} fayl={final.files_written}")


def main():
    online = "--online" in sys.argv

    test_tools()
    test_tool_dispatch()
    test_tool_call_parsing()
    test_message_conversion()
    test_fallback_chain()
    test_model_selection()
    test_scoring()
    test_orchestration_helpers()
    test_cache()
    test_monitor_config()

    if online:
        asyncio.run(run_online_checks())
    else:
        print("\n(ONLINE testlar o'tkazib yuborildi — ishga tushirish: --online)")

    print("\n" + "=" * 60)
    print(f"O'TDI: {PASSED}   YIQILDI: {len(FAILED)}")
    if FAILED:
        print("\nYiqilgan testlar:")
        for f in FAILED:
            print(f"  - {f}")
        sys.exit(1)
    print("BARCHA TESTLAR MUVAFFAQIYATLI O'TDI")


if __name__ == "__main__":
    main()
