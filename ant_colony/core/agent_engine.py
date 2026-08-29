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

from ant_colony.config import (
    PROVIDERS, MODELS_CATALOG, WORKSPACE_DIR, PROJECTS_BASE_DIR, ROLES_DIR,
    WORKSTATIONS, AGENT_CONFIG, SUPPORTED_LANGUAGES, get_language_preference,
)
from ant_colony.runtime.tools import (
    AVAILABLE_TOOLS, set_active_project_dir, get_active_project_dir, list_dir,
)
from ant_colony.llm.models_hub import models_hub
from ant_colony.core.skill_matrix import skill_matrix, DEFAULT_ROLE_DEFINITIONS
from ant_colony.llm.prompt_cache import prompt_cache
from ant_colony.llm.client import llm_client
from ant_colony.llm.usage_ledger import usage_ledger
from ant_colony.core.agent_loop import run_agent, split_reasoning, AgentRunResult

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
        "market_researcher": [
        "bozor tahlili", "raqobatchilar", "raqobat", "bozorni o'rgan", "swot", "tam sam som",
        "analiz rynka", "analiz konkurentov", "issledovanie rynka", "market research", "competitor analysis",
        "marketing strategiya", "narx siyosati", "pricing", "go to market"
    ],
    "content_smm_specialist": [
        "smm", "kontent reja", "post yoz", "kopirayter", "reklama matni", "maqola yoz",
        "telegram post", "instagram post", "kontent", "statya", "tekst dlya sajta", "smm plan",
        "copywriting", "content plan", "blog post", "social media", "reklama"
    ],
    "data_bi_analyst": [
        "ma'lumotlar tahlili", "csv tahlil", "excel tahlil", "bi hisobot", "statistika",
        "analiz dannyh", "otchet excel", "bi analiz", "data analysis", "statistika prodaj",
        "prognoz vyruchki", "daromad prognozi", "funnel", "kpi"
    ],
    "legal_docs_specialist": [
        "shartnoma", "yuridik", "oferta", "nda", "prd", "brd", "nizom", "qonuniy",
        "dogovor", "yuridicheskiy analiz", "polzovatelskoe soglashenie", "terms of service",
        "privacy policy", "contract review", "yuridicheskaya proverka", "reglament"
    ],
    "customer_support_sales": [
        "sotuv skripti", "skript", "mijozlar", "e'tirozlar", "faq", "podderjka",
        "skript prodaj", "otrabotka vozrajeniy", "klienty", "sales script", "support sop",
        "customer success", "skript obshcheniya", "lidlar"
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

    # 2. Kod va loyiha yaratish/yozish buyruqlari (UZ / UZ_CYR / RU / EN)
    creation_verbs = [
        # O'zbek (Lotin)
        "yarat", "yoz", "tuz", "yasa", "qur", "ishlab chiq", "dasturla", "kodini yoz", "generatsiya qil",
        "ochib ber", "tayyorla", "tayyorlab", "tayyorlab ber", "ishga tushir", "run qil", "link ber",
        "loyihasini tuz", "script yoz", "sayt yarat", "bot yoz", "api yoz",
        "sayt qil", "sayt yasab", "ilova yasab", "ilova qil", "ilova yarat", "web sayt",
        "loyiha ochib", "loyiha yaratib", "loyiha tuz", "deploy qil", "publish qil",
        "test yoz", "avtomatlashtir", "integratsiya qil", "installatsiya qil",
        # O'zbek (Kirill)
        "ярат", "ёз", "туз", "яса", "қур", "ишлаб чиқ", "дастурла", "тайёрла", "тайёрлаб",
        "тайёрлаб бер", "ишга тушир", "линк бер", "ойлаб бер", "лойиҳа туз",
        "сайт ярат", "бот ёз", "апи ёз", "илова яса", "лойиҳа очиб",
        # Русский — infinitive va imperative
        "создай", "напиши", "разработай", "сделай", "построй", "запрограммируй", "собери", "сгенерируй",
        "подготовь", "создать", "написать", "разработать", "сделать", "построить", "собрать",
        "запусти", "запустить", "разверни", "развернуть", "опубликуй", "опубликовать",
        "оформи", "оформить", "нарисуй", "нарисовать", "свёрстай", "свёрстать", "сверстай",
        "имплементируй", "имплементировать", "реализуй", "реализовать", "смоделируй",
        "напиши код", "сделай проект", "сделай приложение", "сделай сайт", "сделай страницу",
        "нужен код", "нужна страница", "нужен сайт", "нужен проект", "нужно приложение",
        "хочу проект", "хочу сайт", "хочу приложение", "хочу страницу",
        # English — imperative + noun-phrase intent
        "create", "build", "write", "develop", "make", "code", "generate", "implement", "scaffold",
        "run it", "deploy", "publish", "launch", "host", "spin up", "give me a link",
        "i want", "i need", "please build", "please make", "please create",
    ]

    has_creation_verb = any(_keyword_matches(v, t) for v in creation_verbs)
    has_question_word = any(q in t for q in question_indicators) or t.endswith("?")

    # Kod artefakti indikatorlari — texnologiya, format, muhit
    code_artifact_indicators = [
        # Til va format
        "html", "css", "javascript", "typescript", "python", "golang", "java ", "kotlin",
        "swift", "rust", "php", "ruby", "csharp", "dart",
        # Freymvorklar
        "react", "vue", "angular", "svelte", "next.js", "nextjs", "nuxt", "solidjs",
        "fastapi", "django", "flask", "express", "nestjs", "spring", "laravel", "rails",
        # Ma'lumot va API
        "api", "rest", "graphql", "websocket", "sse ",
        "sql", "sqlite", "postgres", "mongodb", "redis",
        # Ish muhiti va deploy
        "localhost", "docker", "compose", "kubernetes", "netlify", "vercel", "heroku",
        # Artefakt turi
        "website", "web sayt", "web sahifa", "веб-сайт", "веб сайт", "веб-страница", "веб страница",
        "landing page", "лендинг", "лендинг-страница",
        "приложение", "мобильное приложение", "web app", "webapp", "spa ",
        "chrome extension", "extension", "плагин", "модуль", "виджет",
        "компонент", "component", "виджет",
        "dashboard", "dashboard", "админка", "admin panel",
        "animatsiya", "animation", "анимация", "анимации",
        "svetafor", "traffic light", "светофор",
        "canvas", "svg", "webgl", "three.js", "threejs",
        # Bot / avtomatika
        "telegram bot", "discord bot", "slack bot", "chat bot", "чат-бот",
        # Frontend / backend
        "frontend", "backend", "фронтенд", "бэкенд", "бекенд",
    ]
    has_code_artifact = any(_keyword_matches(indicator, t) for indicator in code_artifact_indicators)

    # KUCHLI SIGNAL: creation_verb + code_artifact birga → savol so'zi bo'lsa ham
    # bu kod loyihasi. "Как сделай мне сайт" ham CODE bo'lishi kerak, chunki foydalanuvchi
    # savol emas, buyruq bermoqda. Bu qoida question-first qoidasidan oldin tekshiriladi.
    if has_creation_verb and has_code_artifact:
        return True

    # Agar sof savol so'zi bo'lsa va yaratish buyrug'i bo'lmasa → suhbat/savol
    if has_question_word and not has_creation_verb:
        return False

    # Yolg'iz kod artefakti (masalan "sayt", "extension", "landing") + hech qanday
    # savol so'zi yo'q → foydalanuvchi buyurmoqda.
    if has_creation_verb or (has_code_artifact and not has_question_word):
        return True

    return False


def create_dynamic_role(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    PM so'ragan yangi mutaxassis rolini yaratadi.

    Yaratiladi: `roles/<id>.md` yo'riqnomasi + ELO matritsasida yozuv.
    Shundan keyin rol boshqa oddiy rollar bilan bir xil ishlaydi: unga model
    tayinlanadi, ishi baholanadi va u qayta ishlatiladi.

    Rol id'si tozalanadi — foydalanuvchi/model bergan matn fayl yo'liga
    aylanadi, shuning uchun `../` kabi belgilar o'tkazilmaydi.
    """
    raw_id = str(spec.get("id") or "").strip().lower()
    role_id = re.sub(r"[^a-z0-9_]+", "_", raw_id).strip("_")[:48]
    if not role_id:
        return None

    name = str(spec.get("name") or role_id.replace("_", " ").title()).strip()[:80]
    description = str(spec.get("description") or "").strip()[:400]
    category = str(spec.get("category") or "general").strip()
    system_prompt = str(spec.get("system_prompt") or "").strip()

    md_file = f"{role_id}.md"
    md_path = ROLES_DIR / md_file
    if not _is_within_dir(ROLES_DIR, md_path):
        return None

    if not md_path.exists():
        body = system_prompt or (
            f"Sen — {name}. {description}\n\n"
            "Vazifani sifatli, to'liq va tekshiriladigan qilib bajar."
        )
        content = (
            f"# {name}\n\n"
            f"## Описание роли\n{description or name}\n\n"
            f"## Системная инструкция\n{body}\n\n"
            f"## Ключевые навыки\n"
            f"- Профильная экспертиза в своей области\n"
            f"- Полное и проверяемое выполнение задачи\n"
        )
        try:
            ROLES_DIR.mkdir(parents=True, exist_ok=True)
            md_path.write_text(content, encoding="utf-8")
        except OSError:
            return None

    role_dict = {
        "id": role_id,
        "name": name,
        "description": description,
        "category": category,
        "md_file": md_file,
        "initial_model": skill_matrix.get_best_model_for_role("frontend_architect"),
        "dynamic": True,
    }
    try:
        skill_matrix.register_custom_role(role_dict)
    except Exception:
        return None
    return role_dict


def _is_within_dir(base: Path, target: Path) -> bool:
    """Yo'l `base` ichidami? Rol id'si orqali papkadan chiqib ketishga qarshi."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def is_conversational_query(text: str) -> bool:
    """Tekshiradi: topshiriq savol/suhbatmi (kod loyihasi emasmi)?"""
    return not is_code_creation_intent(text)


def detect_query_lang(text: str) -> str:
    """Foydalanuvchi topshirig'i qaysi tilda: en / uz (Lotin) / uz_cyr (Kirill) / ru?

    MUHIM: har qanday kirill matni `ru` deb belgilab bo'lmaydi — o'zbek kirill
    alifbosida faqat o'zbek tiliga xos belgilar (ў, қ, ғ, ҳ) va so'zlar bor.
    Shuning uchun avval o'zbek-kirill aniqlanadi, keyin ruscha.
    """
    t = (text or "").lower()
    cyrillic_chars = sum(1 for c in t if '\u0400' <= c <= '\u04FF')
    if cyrillic_chars == 0:
        # Kirill umuman yo'q — lotin asosli tillar
        en_words = ["how", "what", "create", "make", "build", "hello", "can", "you", "please",
                    "python", "react", "api", "write", "generate", "explain", "status", "help"]
        uz_lat_words = ["qanday", "nima", "qiling", "yarat", "kerak", "uchun", "bilan",
                        "qo'lingdan", "salom", "loyiha", "men", "va", "ham", "yoz", "ber"]
        if any(w in t for w in uz_lat_words):
            return "uz"
        if any(w in t for w in en_words):
            return "en"
        # Lotin matn, lekin aniq emas — odatiy holda o'zbek (Lotin) deb olaylik.
        return "uz"

    # Kirill matni mavjud — o'zbek-kirill yoki rusni farqlaymiz.
    uz_cyr_unique = set("ўқғҳ")  # o'zbek kirilliga xos belgilar
    if any(ch in uz_cyr_unique for ch in t):
        return "uz_cyr"
    # Qisqa so'zlar (masalan "ва") ruscha so'zlar ichida tasodifiy uchib qolishi
    # mumkin ("поддерживаешь" ichida "ва"). Shuning uchun so'z chegarasi bilan
    # tekshiramiz — aks holda noto'g'ri uz_cyr deb belgilanadi.
    uz_cyr_words = ["ўзбек", "куни", "ва", "билан", "учун", "керак", "сиз", "мен",
                    "лоиха", "тил", "қандай", "қилинг", "ярат", "салом", "ҳам",
                    "менга", "сенга", "биз", "улар", "илтимос", "яхши"]
    _cyr_word_re = re.compile(r"(?<![\wЀ-ӿ])(?:%s)(?![\wЀ-ӿ])" % "|".join(map(re.escape, uz_cyr_words)))
    if _cyr_word_re.search(t):
        return "uz_cyr"
    # Qolgan kirill — ruscha
    return "ru"


def resolve_response_language(preferred: str, detected: str) -> str:
    """Agent qaysi tilda javob berishini aniqlaydi.

    `preferred` — foydalanuvchi tanlagan UI tili (`auto` bo'lishi mumkin).
    `auto` bo'lsa aniqlangan (`detected`) til ishlatiladi.
    """
    preferred = (preferred or "auto").lower()
    if preferred in SUPPORTED_LANGUAGES and preferred != "auto":
        return preferred
    if detected in ("en", "uz", "uz_cyr", "ru"):
        return detected
    return "uz"


# LLM javob bera olmaganda ishlatiladigan fallback javoblar (til bo'yicha).
FALLBACK_ANSWERS: Dict[str, str] = {
    "ru": (
        "Я — **Project Manager** и центральный оркестратор платформы **Ant Colony AI**.\n\n"
        "### Мои основные возможности:\n"
        "1. **Универсальная разработка:** Python (FastAPI, Django), Node.js (React, Vue, Express), Go, PHP (Laravel), Rust, HTML5/CSS3/JS анимации.\n"
        "2. **12 специализированных ролей ИИ:** Архитектор, Frontend, Backend, UI/UX дизайнер, QA инженер тестирования, Аудитор безопасности, DevOps инженер, Аналитик данных.\n"
        "3. **Автоматический контроль качества (QA и Безопасность):** Проверка синтаксиса, анализ структуры DOM и выявление уязвимостей с автоматическим исправлением ошибок.\n"
        "4. **Автономное рабочее окружение:** Создание готовых проектов в папке `04_Loyihalar` на рабочем столе и запуск через встроенный терминал.\n\n"
        "Поставьте любую задачу (например: *'Создать REST API авторизации на FastAPI'* или *'Интерактивный неоновый таймер на HTML/CSS/JS'*), и я организую команду ИИ-агентов для ее выполнения!"
    ),
    "uz": (
        "Men **Ant Colony AI** universal agentlar platformasining Markaziy Project Manageriman.\n\n"
        "### Asosiy imkoniyatlarim:\n"
        "1. **Universal dasturlash:** Python (FastAPI/Django), Node.js (React/Vue/Express), Go, PHP (Laravel), Rust, HTML/CSS/JS animatsiyalar.\n"
        "2. **12 ta ixtisoslashgan rol:** Arxitektor, Frontend, Backend, UI/UX, QA Test, Xavfsizlik auditi, DevOps, Ma'lumotlar tahlili.\n"
        "3. **Avtomatik sifat tekshiruvi (QA & Security):** Kod sintaksisi, DOM bog'liqliklari va zaifliklarni deterministik tekshirish va xatolarni avtomatik tuzatish.\n"
        "4. **Haqiqiy ishchi muhit:** Desktop `04_Loyihalar` katalogida mustaqil loyihalar yaratish va terminal asboblari orqali ishga tushirish.\n\n"
        "Menga aniq topshiriq bering (masalan: *\"FastAPI da foydalanuvchilar ro'yxati API sini yoz\"* yoki *\"Neon kalkulyator veb ilovasi\"*), men mutaxassislarni ishga solib, to'liq tayyorlab beraman!"
    ),
    "uz_cyr": (
        "Мен **Ant Colony AI** универсал агентлар платформасининг Марказий Project Managerиман.\n\n"
        "### Асосий имкониятларим:\n"
        "1. **Универсал дастурлаш:** Python (FastAPI/Django), Node.js (React/Vue/Express), Go, PHP (Laravel), Rust, HTML/CSS/JS анимациялар.\n"
        "2. **12 та ихтисослашган рол:** Архитектор, Frontend, Backend, UI/UX, QA Test, Хавфсизлик аудити, DevOps, Маълумотлар тахлили.\n"
        "3. **Автоматик сифат текшируви (QA & Security):** Код синтаксиси, DOM боғлиқликлари ва заифликларни детерминистик текшириш ва хатоларни автоматик тузатиш.\n"
        "4. **Ҳақиқий ишчи муҳит:** Desktop `04_Loyihalar` каталогида мустақил лойиҳалар яратиш ва терминал асбоблари орқали ишга тушириш.\n\n"
        "Менга аниқ топшириқ берг (масалан: *\"FastAPI да фойдаланувчилар рўйхати API сини ёз\"* ёки *\"Неон калкулятор веб иловаси\"*), мен мутахассисларни ишга солиб, тўлиқ тайёрлаб бераман!"
    ),
    "en": (
        "I am the **Project Manager** and central orchestrator of the **Ant Colony AI** platform.\n\n"
        "### My core capabilities:\n"
        "1. **Universal development:** Python (FastAPI, Django), Node.js (React, Vue, Express), Go, PHP (Laravel), Rust, HTML5/CSS3/JS animations.\n"
        "2. **12 specialized AI roles:** Architect, Frontend, Backend, UI/UX designer, QA test engineer, Security auditor, DevOps engineer, Data analyst.\n"
        "3. **Automatic quality control (QA & Security):** Deterministic checks of code syntax, DOM structure and vulnerability detection with automatic error fixing.\n"
        "4. **Real autonomous workspace:** Creating finished projects in the `04_Loyihalar` folder on the desktop and running them via built-in terminal tools.\n\n"
        "Give me a concrete task (e.g. *'Build a FastAPI auth REST API'* or *'Neon calculator web app'*) and I will spin up the specialist agents to deliver it complete!"
    ),
}


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


def _clean_subtasks(raw: Any) -> List[Dict[str, str]]:
    """
    PM qaytargan `subtasks` ro'yxatini tozalaydi.

    LLM bu maydonni turli ko'rinishda qaytarishi mumkin (matnlar ro'yxati,
    yarim to'ldirilgan lug'atlar, o'nlab element). Mutaxassisga beriladigan
    kontekst barqaror bo'lishi uchun bu yerda bitta shaklga keltiramiz va
    12 ta bilan cheklaymiz — undan ortig'i kontekstni to'ldirib, foydali
    ma'lumotni siqib chiqaradi.
    """
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, str]] = []
    for item in raw[:12]:
        if isinstance(item, str):
            title = item.strip()
            if title:
                out.append({"title": title, "file": "", "detail": "", "done_when": ""})
            continue
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("step") or item.get("name") or "").strip()
        if not title:
            continue
        out.append({
            "title": title,
            "file": str(item.get("file") or "").strip(),
            "detail": str(item.get("detail") or item.get("description") or "").strip(),
            "done_when": str(item.get("done_when") or item.get("acceptance") or "").strip(),
        })
    return out


def _format_subtasks(subtasks: List[Dict[str, str]]) -> str:
    """Mutaxassis agent uchun o'qiladigan ish taqsimoti matni."""
    if not subtasks:
        return ""
    rows = []
    for i, st in enumerate(subtasks, 1):
        line = f"{i}. {st['title']}"
        if st["file"]:
            line += f"  [fayl: {st['file']}]"
        if st["detail"]:
            line += f"\n   - Nima qilinadi: {st['detail']}"
        if st["done_when"]:
            line += f"\n   - Tugadi hisoblanadi: {st['done_when']}"
        rows.append(line)
    return (
        "ISH TAQSIMOTI (Project Manager tuzgan — shu tartibda bajaring, "
        "har bir qadamni tugallamasdan keyingisiga o'tmang):\n"
        + "\n".join(rows)
        + "\n"
    )


def plan_quality_issues(spec: Dict[str, Any]) -> List[str]:
    """Returns missing verifiable parts of a code-project plan."""
    if spec.get("task_type") not in (None, "code_project"):
        return []
    issues: List[str] = []
    files = spec.get("files") if isinstance(spec.get("files"), list) else []
    criteria = spec.get("acceptance_criteria") if isinstance(spec.get("acceptance_criteria"), list) else []
    subtasks = _clean_subtasks(spec.get("subtasks"))
    if not files:
        issues.append("yaratiladigan fayllar ko'rsatilmagan")
    if not criteria:
        issues.append("qabul mezonlari ko'rsatilmagan")
    if not 3 <= len(subtasks) <= 8:
        issues.append("subtasklar soni 3–8 oralig'ida emas")
    if subtasks and any(not item["done_when"] for item in subtasks):
        issues.append("subtasklarda tekshiriladigan done_when maydoni yo'q")
    if not str(spec.get("verification_command") or "").strip():
        issues.append("tekshiruv buyrug'i ko'rsatilmagan")
    return issues


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
        from ant_colony.core.agent_loop import parse_text_tool_calls
        content = raw_message.get("content", "") or ""
        reasoning, clean = split_reasoning(content)
        calls, clean = parse_text_tool_calls(clean)
        tool_call = {"tool": calls[0]["name"], "params": calls[0]["arguments"]} if calls else None
        return reasoning, clean, tool_call

    # --- PM: tuzilmali reja ---
    async def _plan_with_pm(
        self, task_prompt: str, pm_model: str, pm_md: str,
        default_role: str, custom_keys: Optional[Dict[str, str]],
        language: str = "auto",
    ) -> Dict[str, Any]:
        role_menu = "\n".join(
            f"- `{r['id']}` — {r['description']}" for r in DEFAULT_ROLE_DEFINITIONS
            if r["id"] != "pm_orchestrator"
        )

        ws_summary = get_workspace_projects_summary()

        # PM uzoq muddatli xotira konteksti — oldingi loyihalar, kelajakdagi rejalar
        pm_mem_context = ""
        last_project_note = ""
        try:
            from ant_colony.core.pm_memory import get_memory
            mem = get_memory()
            if mem:
                snippet = mem.as_context_snippet(max_projects=5)
                if snippet:
                    pm_mem_context = f"\n## MENIN UZOQ MUDDATLI XOTIRAM (avvalgi sessiyalardan):\n{snippet}\n\n"
                # Eng so'nggi loyiha — alohida ta'kidlangan blok, xatosiz javob berish uchun
                snap = mem.snapshot()
                completed = snap.get("completed_projects", [])
                if completed:
                    last = completed[0]
                    files_list = ", ".join(last.get("files", [])[:8]) or "fayllar yozilmagan"
                    last_project_note = (
                        "\n## ⚡ ENG SO'NGGI LOYIHA (aynan shu — hallutsinatsiya qilmang!):\n"
                        f"- **Topshiriq:** {last.get('task', '?')}\n"
                        f"- **Papka:** `{last.get('project_dir', '?')}`\n"
                        f"- **Yaratilgan fayllar ({last.get('files_count', 0)}):** {files_list}\n"
                        f"- **Ball:** {last.get('score', '—')}/100 · **Vaqt:** {last.get('duration_s', 0)}s\n"
                        f"- **Tugagan:** {last.get('iso', '?')}\n"
                        f"- **Xulosa:** {last.get('summary', '—')}\n\n"
                        "AGAR foydalanuvchi so'nggi/hozirgi loyiha haqida so'rasa (masalan: "
                        "'loyiha tugadimi', 'qayerda', 'link ber', 'localhost'), "
                        "AYNAN yuqoridagi ma'lumotdan foydalaning. Boshqa papkalar ro'yxatini yozmang!\n\n"
                    )
        except Exception:
            pass

        # --- Til hal qilish (response language resolution) ---
        detected_lang = detect_query_lang(task_prompt)
        resp_lang = resolve_response_language(language, detected_lang)
        lang_name = SUPPORTED_LANGUAGES.get(resp_lang, SUPPORTED_LANGUAGES["uz"])

        prompt = (
            f"Foydalanuvchi topshirig'i / Запрос пользователя: \"{task_prompt}\"\n\n"
            "Siz Ant Colony AI universal agentlar platformasining Bosh Project Managerisiz.\n"
            f"## ISHCHI MUHIT VA MAVJUD LOYIHALAR TARIXI (FAQAT HAQIQIY FAKTLAR):\n{ws_summary}\n\n"
            + last_project_note
            + pm_mem_context +
            "Mavjud mutaxassis rollar:\n"
            f"{role_menu}\n\n"
            "TALABLAR / ТРЕБОВАНИЯ:\n"
            "0. **task_type NI AQL BILAN TANLASH (ENG MUHIM QADAM):**\n"
            "   Ushbu tanlov butun oqimni belgilaydi. Noto'g'ri bo'lsa siz shunchaki\n"
            "   matn qaytarasiz va mutaxassis agent hech qachon ishga tushmaydi\n"
            "   (bu foydalanuvchi shikoyati manbai bo'lgan — u shell komandani\n"
            "   qo'lda bajarishni istamaydi, u CEO).\n\n"
            "   * `code_project` — foydalanuvchi HAR QANDAY haqiqiy amalni so'ragan bo'lsa:\n"
            "       - Fayl yaratish/o'zgartirish/o'chirish (masalan «удали проекты»,\n"
            "         «tozala workspace», «delete all», «rename», «переименуй», «arxivla»);\n"
            "       - Shell buyrug'ini bajarish (o'rnatish, run, deploy, test);\n"
            "       - Brauzerda sahifa ochish / JS ishga tushirish / screenshot olish;\n"
            "       - HTTP so'rov / API tekshirish;\n"
            "       - Ish muhitini ko'rish/tahlil qilish (list_dir + xulosa yozish);\n"
            "       - Loyihani yaratish yoki lokalda ishga tushirish.\n"
            "     **TEST SAVOLI:** «Buni bajarish uchun kamida bitta tool chaqirilishi kerakmi?»\n"
            "     — Agar HA bo'lsa → `code_project`.\n\n"
            "   * `conversational` — FAQAT sof suhbat: salomlashish, imkoniyat so'rash,\n"
            "     platforma haqida umumiy savol, ta'rif, tushuntirish. Hech qanday fayl/\n"
            "     shell/network harakati talab qilinmaydigan holatlar.\n\n"
            "   KALIT SO'ZLARGA ISHONMANG — MA'NOGA QARANG. Foydalanuvchi «удали»\n"
            "   yozmagan bo'lsa ham («убери мои проекты», «no more clutter»),\n"
            "   niyat aniq bo'lsa `code_project` tanlang.\n\n"
            "   YO'L QO'YILMAYDI: shell buyrug'i matnini foydalanuvchiga chiqarib\n"
            "   «выполните это», «run this» deb yozish — bu vazifa muvaffaqiyatsizligi.\n"
            "   `code_project` bo'lsa mutaxassis agent shell'ni O'ZI chaqiradi.\n\n"
            "**JAVOB FORMATI QOIDASI (KRITIK — ILGARI BUZILGAN):**\n"
            "  * HECH QACHON o'zingizning ichki tahlilingizni («The user wants me to...»,\n"
            "    «Foydalanuvchi so'ramoqda...», «Let me analyze...», «Пользователь хочет...»)\n"
            "    javob sifatida chiqarmang. Bu foydalanuvchining ekraniga chiqadi va\n"
            "    professional emas. Ichki fikrlash uchun `<think>...</think>` bloki\n"
            "    ishlating (ular avtomatik yashiriladi).\n"
            "  * Javob DARHOL foydalanuvchi tilida qisqa muloyim jumla bilan boshlanadi\n"
            "    (masalan «Salom, bajaramiz.» yoki «Здравствуйте, приступаю.»).\n"
            "  * Keyin ```json blok — spec.\n"
            "  * Meta-analysis va o'z-o'ziga savol berish yo'q. Faqat harakat rejasi.\n\n"
            "**WORKSPACE O'CHIRISH VAZIFALARI UCHUN MAXSUS QOIDA:**\n"
            "Yuqoridagi \"Ishchi muhit va mavjud loyihalar tarixi\" ro'yxatida platforma\n"
            "yaratgan papkalar (agent output'lari — svetafor, soat, ilovalar) va foydalanuvchining\n"
            "o'z ish papkalari (masalan `andijon-*`, `paxtaobod-*`, `markaziy-*`, real\n"
            "boshqaruv panellari) aralash bo'lishi mumkin.\n"
            "Agar foydalanuvchi «o'chir» / «удали» / «delete» desa, LEKIN «hammasin emas»,\n"
            "«не все», «not all», «faqat sen yaratgan» kabi cheklov qo'ysa — REJA'da\n"
            "AYNAN QAYSI papkalar o'chirilishini spec'da yozib bering (files ro'yxatida\n"
            "yoki subtasks ichida). Real foydalanuvchi papkalarini (aniq bo'lmasa)\n"
            "TEGIB BO'LMAYDI. Shubha bo'lsa foydalanuvchidan tasdiq so'rang\n"
            "(direct_answer bilan qisqa muloyim savol berib).\n\n"
            "1. MUHIM TIL QOIDASI / ЯЗЫКОВОЕ ПРАВИЛО (CRITICAL):\n"
            "   Foydalanuvchi xabarida qaysi tildan foydalangan bo'lsa (ruscha, o'zbekcha, inglizcha va h.k.), "
            "rejangizni, tahlilingizni va javobingizni AYNAN O'SHA TILDA yozing. "
            "Если пользователь написал по-русски — отвечайте по-русски. Agar o'zbekcha yozgan bo'lsa — o'zbek tilida javob bering. If English — reply in English.\n"
            f"   HALQIQI JAVOB TILI / ОБЯЗАТЕЛЬНЫЙ ЯЗЫК ОТВЕТА: **{lang_name}**. "
            "Barcha rejalar, tahlillar va foydalanuvchiga qaratilgan matnlar AYNAN shu tilda bo'lishi shart.\n\n"
            "   MUROJAAT QOIDASI / ОБРАЩЕНИЕ (MAJBURIY):\n"
            "   * Foydalanuvchini HECH QACHON `ustoz`, `xo'jayin`, `ustad`, `хозяин`, `господин`, `master`, `sir`, `sensei` "
            "     yoki shunga o'xshash iyerarxik/qullik so'zlari bilan chaqirmang.\n"
            "   * Neytral va professional muloyimlik ishlating: o'zbekcha `Assalomu alaykum`, `sizga`, `sizning topshirig'ingiz`; "
            "     ruscha `Здравствуйте`, `ваш запрос`, `вы`; inglizcha `Hello`, `your request`, `you`.\n"
            "   * Kerak bo'lganda foydalanuvchini `CEO` (mos kontekstda) yoki oddiy `siz/вы/you` deb ataysiz — boshqasi yo'q.\n\n"
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
            "3b. AGAR yuqoridagi rollar orasida vazifaga MOS mutaxassis bo'lmasa — YANGI rol yarating.\n"
            "   Faqat haqiqatan kerak bo'lsa qiling: mavjud rol 70% mos kelsa, o'shani ishlating.\n"
            "   JSON ichida `specialist_role` sifatida yangi rol id'sini bering va `new_role` blokini qo'shing:\n"
            "```json\n"
            "{\n"
            '  "task_type": "code_project",\n'
            '  "specialist_role": "game_designer",\n'
            '  "new_role": {\n'
            '    "id": "game_designer",\n'
            '    "name": "Game Designer",\n'
            '    "description": "O\'yin mexanikasi, level dizayni va balans mutaxassisi",\n'
            '    "category": "frontend_ui",\n'
            '    "system_prompt": "Rol uchun to\'liq tizim yo\'riqnomasi: mas\'uliyat doirasi, ish uslubi, sifat mezonlari..."\n'
            "  }\n"
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
            '  "role_reason": "nega aynan shu rol tanlandi — bir jumla",\n'
            '  "subtasks": [\n'
            '    {"title": "qadam nomi", "file": "shu qadam tegadigan fayl", "detail": "aynan nima qilinadi", "done_when": "qanday tekshiriladi"}\n'
            '  ],\n'
            '  "verification_command": "natijani tekshiruvchi terminal buyrug\'i yoki bo\'sh satr"\n'
            "}\n"
            "```\n\n"
            "5. DEKOMPOZITSIYA SIFATI (MAJBURIY — reja boyicha mutaxassis agent ishlaydi):\n"
            "   * `subtasks` — 3 tadan 8 tagacha. Har biri BITTA aniq natijaga olib kelsin. Kamroq bolsa mutaxassis nima qilishni bilmaydi, kop bolsa qadamlar sigmaydi.\n"
            "   * Har bir subtask `file` maydoni `files` royxatidagi fayllardan biri bolsin. Faylga tegmaydigan qadam (masalan tahlil qilish) — subtask EMAS.\n"
            "   * `done_when` TEKSHIRILADIGAN bolsin: ishlaydi / chiroyli / togri — YAROQSIZ. Yaroqli: sahifa 200 qaytaradi, `pytest -q` xatosiz otadi, formada 3 ta maydon bor.\n"
            "   * Qadamlar BAJARILISH TARTIBIDA: avval tuzilma va konfiguratsiya, keyin mantiq, oxirida test va hujjat. Keyingi qadam oldingisining natijasiga tayansin.\n"
            "   * TOLDIRUVCHI qadam yozmang (loyihani rejalashtirish, kod yozish, yakunlash) — ular hech qanday malumot bermaydi.\n\n"
            "6. ROL TANLASH QOIDASI (MAJBURIY):\n"
            "   * `specialist_role` ni vazifaning ASOSIY NATIJASIGA qarab tanlang, ishlatiladigan texnologiyaga qarab emas: sayt interfeysi — `frontend_architect`, API yoki server — `backend_engineer`, malumot tahlili — `data_bi_analyst`, mobil ilova — `mobile_developer`.\n"
            "   * Odat boyicha `backend_engineer` ni tanlamang — bu eng kop uchraydigan xato.\n"
            "   * `role_reason` da tanlovni bir jumlada asoslang. Asoslay olmasangiz — rol notogri.\n"
            "   * Faqat royxatdagi `id` larni yozing. Mos rol bolmasa — 3b bandidagi `new_role` blokini ishlating."
        )

        with usage_ledger.agent_scope("Project Manager", role="pm_orchestrator", phase="planning"):
            res = await llm_client.complete(
                pm_model,
                [{"role": "system", "content": pm_md}, {"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=3000, custom_keys=custom_keys
            )

        is_conv = is_conversational_query(task_prompt)

        if not res["success"]:
            if is_conv:
                default_answer = FALLBACK_ANSWERS.get(resp_lang, FALLBACK_ANSWERS["uz"])
                fallback_reasoning = (
                    f"Foydalanuvchi {lang_name} tilida imkoniyatlarni so'radi — "
                    "to'liq fallback javob berildi."
                )
                return {
                    "ok": True, "error": None,
                    "plan_text": default_answer, "reasoning": fallback_reasoning,
                    "model_used": pm_model,
                    "spec": {"task_type": "conversational", "direct_answer": default_answer, "specialist_role": default_role, "files": [], "steps": [], "acceptance_criteria": [], "subtasks": [], "role_reason": "", "verification_command": "", "project_name": None},
                    "usage": {},
                }

            return {
                "ok": False, "error": res.get("error", ""),
                "plan_text": "", "reasoning": "", "model_used": pm_model,
                "spec": {"task_type": "code_project", "specialist_role": default_role, "files": [], "steps": [],
                         "acceptance_criteria": [], "subtasks": [], "role_reason": "", "verification_command": "", "project_name": None},
                "usage": {},
            }

        inline_reasoning, text = split_reasoning(res["text"])
        reasoning = (res.get("reasoning") or "") + ("\n" + inline_reasoning if inline_reasoning else "")
        spec = extract_json_block(text) or {}

        # MUHIM: ilgari regex `is_conv` PM'ning O'Z qarorini majburan bekor
        # qilardi. Natijada foydalanuvchi "проекты удали" desa (regex'da yo'q
        # so'z), PM to'g'ri "code_project" desa ham biz uni "conversational"
        # ga o'tkazib PM shell command bermay matn yozib qo'yardi — CEO shikoyati.
        #
        # Yangi qoida: PM'ning o'zi ancha aqlliroq. Uning JSON spec'idagi
        # aniq qaror hurmat qilinadi. Regex faqat PM aytmaganda default sifatida.
        pm_declared = spec.get("task_type") if isinstance(spec, dict) else None
        if pm_declared in ("conversational", "code_project", "platform_audit"):
            task_type = pm_declared
        else:
            task_type = "conversational" if is_conv else "code_project"
        spec["task_type"] = task_type

        plan_issues = plan_quality_issues(spec)
        if plan_issues:
            repair_prompt = (
                f"{prompt}\n\n"
                "Sizning avvalgi rejangiz tekshiruvdan o'tmadi. Quyidagi kamchiliklarni to'ldiring: "
                + "; ".join(plan_issues)
                + "\nFaqat yaxshilangan qisqa reja va to'liq JSON blok qaytaring."
            )
            with usage_ledger.agent_scope("Project Manager", role="pm_orchestrator", phase="plan_repair"):
                repair_res = await llm_client.complete(
                    pm_model,
                    [{"role": "system", "content": pm_md}, {"role": "user", "content": repair_prompt}],
                    temperature=0.1, max_tokens=3000, custom_keys=custom_keys,
                )
            if repair_res.get("success"):
                repaired_text = repair_res.get("text") or ""
                repaired_spec = extract_json_block(repaired_text) or {}
                repaired_spec["task_type"] = repaired_spec.get("task_type") or task_type
                if len(plan_quality_issues(repaired_spec)) < len(plan_issues):
                    spec = repaired_spec
                    text = repaired_text
                    plan_issues = plan_quality_issues(spec)
        role = spec.get("specialist_role")
        valid_roles = {r["id"] for r in DEFAULT_ROLE_DEFINITIONS}

        # PM mavjud rollar orasidan mosini topmasa, yangi mutaxassis yaratishi mumkin.
        # Bu real ehtiyoj: platformada 19 ta rol bor, lekin barcha soha qamralmagan.
        created_role = None
        if role not in valid_roles and isinstance(spec.get("new_role"), dict):
            created_role = create_dynamic_role(spec["new_role"])
            if created_role:
                role = created_role["id"]
                valid_roles.add(role)

        if role not in valid_roles or role == "pm_orchestrator":
            role = default_role

        # JSON blokini odamga ko'rsatiladigan matndan olib tashlaymiz.
        plan_text = _JSON_BLOCK_RE.sub("", text).strip() or text.strip()
        if created_role:
            spec["_created_role"] = created_role

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
                "subtasks": _clean_subtasks(spec.get("subtasks")),
                "role_reason": str(spec.get("role_reason") or "").strip(),
                "verification_command": spec.get("verification_command") or "",
                "plan_quality": {
                    "complete": not plan_issues,
                    "issues": plan_issues,
                },
            },
        }

    async def run_orchestrated_task_stream(
        self,
        task_prompt: str,
        custom_keys: Optional[Dict[str, str]] = None,
        language: str = "auto",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.time()
        # Orkestratsiya davomida fon pinglari to'xtaydi — bepul kvota agentlarga kerak.
        models_hub.mark_busy(600)

        try:
            async for event in self._orchestrate(task_prompt, custom_keys, start_time, language):
                yield sanitize_event(event)
        finally:
            models_hub.clear_busy()

    async def _orchestrate(
        self, task_prompt: str,
        custom_keys: Optional[Dict[str, str]],
        start_time: float,
        language: str = "auto",
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
        plan = await self._plan_with_pm(task_prompt, pm_model, pm_md, heuristic_role, custom_keys, language)
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
            # MUHIM: oddiy suhbat — bu loyiha EMAS.
            # Ilgari bu yerda final_score=100 va soxta score_breakdown
            # (qa/artifacts/execution = 100) yuborilardi. Natijada har bir
            # "salom" ham "loyiha muvaffaqiyatli yakunlandi, ball 100" bo'lib
            # ko'rinar va PM xotirasiga bajarilgan loyiha sifatida yozilardi.
            yield {
                "type": "orchestration_completed",
                "task_type": "conversational",
                "duration_seconds": round(time.time() - start_time, 2),
                "final_score": None,
                "score_breakdown": None,
                "created_files": [],
                "eval_summary": None,
                # Oddiy suhbat ham token sarflaydi — foydalanuvchi buni ko'rsin.
                "token_usage": usage_ledger.task_usage_block(usage_ledger.current_task_id() or ""),
            }
            return

        # PM yangi mutaxassis yaratgan bo'lsa — buni foydalanuvchi ko'rsin.
        created_role = spec.get("_created_role")
        if created_role:
            yield {
                "type": "role_created",
                "station": "pm",
                "role_id": created_role["id"],
                "role_name": created_role["name"],
                "description": created_role.get("description", ""),
                "message": f"Создан новый специалист: {created_role['name']}",
            }

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
            # PM nega aynan shu rolni tanlaganini foydalanuvchi ko'rsin —
            # noto'g'ri taqsimot darhol sezilsin.
            "role_reason": spec.get("role_reason") or "",
            "subtasks_count": len(spec.get("subtasks") or []),
            "plan_quality": spec.get("plan_quality") or {},
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
                + _format_subtasks(spec.get("subtasks") or [])
                + (f"Yaratilishi kerak bo'lgan fayllar: {', '.join(spec['files'])}\n" if spec["files"] else "")
                + (f"Qadamlar:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(spec["steps"])) + "\n" if spec["steps"] else "")
                + (f"Qabul shartlari:\n" + "\n".join(f"- {c}" for c in spec["acceptance_criteria"]) + "\n" if spec["acceptance_criteria"] else "")
                + "\n**BAJARISH QOIDASI (MAJBURIY):** Foydalanuvchi CEO — natija kutmoqda, ko'rsatma emas.\n"
                + "  * Har qanday shell buyrug'i (`rm`, `mkdir`, `cp`, `npm install`, `pytest` va h.k.)\n"
                + "    darhol `run_shell_command` orqali BAJARILISHI kerak.\n"
                + "  * Buyruqni oddiy matn qilib chiqarib «выполните это», «run this» deb yozish\n"
                + "    — vazifa muvaffaqiyatsizligi hisoblanadi.\n"
                + "  * O'chirish/tozalash vazifalarida: avval `list_dir` bilan tekshiring, keyin\n"
                + "    ANIQ nomlar bilan `rm -rf <nom1> <nom2>` chaqiring (yulduzcha yoki `/`, `~`,\n"
                + "    `..` ishlatmang), oxirida yana `list_dir` bilan natijani tasdiqlang.\n\n"
                + "**TEST + SCREENSHOT (MAJBURIY YAKUNIY QADAM):**\n"
                + "Vazifani tugatgach, natijani O'ZINGIZ tekshirasiz va foydalanuvchiga isbot beriladi.\n"
                + "1. Test/pytest fayl bo'lsa → `run_shell_command('pytest -q')` yoki `npm test`.\n"
                + "   Xato bo'lsa tuzating va qayta ishga tushiring.\n"
                + "2. Sayt / veb-loyiha (index.html, React, Flask, FastAPI):\n"
                + "   * `run_shell_command_background` bilan lokal server chiqaring\n"
                + "     (uvicorn / `python -m http.server` / `npm run dev`)\n"
                + "   * `browser_screenshot(url='http://127.0.0.1:PORT', full_page=True)` chaqiring\n"
                + "   * Qaytgan `path` ni yakuniy javobingizga ALOHIDA QATORDA yozing:\n"
                + "         SCREENSHOT: /full/path/to/shot.png\n"
                + "     Bu marker PM Console'da avtomatik rasm sifatida ko'rsatiladi.\n"
                + "3. Konsol/skript loyiha bo'lsa — `execute_python` yoki `run_shell_command`\n"
                + "   bilan bir marta ishga tushiring va stdout natijasini yakunda yozing.\n"
                + "4. API/endpoint bo'lsa — `http_get` yoki `browser_execute_js` bilan chaqiring.\n"
                + "Bu qadam O'TKAZIB YUBORILMAYDI. Test va screenshot yo'q → vazifa yakunlanmagan.\n"
            )

        coder_result: Optional[AgentRunResult] = None
        async for event in run_agent(
            station="coder", agent_name=coder_display, model_id=coder_model,
            role_md=coder_md, task=task_prompt, context=coder_context,
            tool_names=["write_file", "edit_file", "read_file", "list_dir",
                        "find_relevant_files", "verify_code_syntax",
                        "run_shell_command", "run_shell_command_background",
                        "bg_status", "bg_stop", "execute_python", "calculate",
                        "http_get", "http_post", "browser_navigate",
                        "browser_execute_js", "browser_screenshot"],
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
        from ant_colony.runtime.tools import verify_code_syntax
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
                            "find_relevant_files", "verify_code_syntax",
                            "run_shell_command", "run_shell_command_background",
                            "bg_status", "bg_stop", "execute_python",
                            "http_get", "browser_navigate", "browser_execute_js"],
                # Ilgari floor=4 edi — repair'ga shu 14 ta asbob berilgach (2 qatorda
                # yuqorida), 4 qadamda `write_file`/`edit_file`ga yetib borish deyarli
                # imkonsiz edi (docs/HANDOFF.md T15). Floor 8'ga ko'tarildi.
                max_steps=max(8, AGENT_CONFIG["max_tool_steps"] // 2),
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

        # Coder xulosasida "SCREENSHOT: <yo'l>" marker'larini topamiz — bularni
        # PM Console'da rasm sifatida ko'rsatish uchun alohida ajratamiz.
        # Marker qoidasi (coder promptida keyingi commit'da qo'shiladi):
        # vazifadan keyin browser_screenshot chaqiring va yakuniga
        # "SCREENSHOT: <path>" yozing.
        screenshots: List[str] = []
        try:
            for m in re.finditer(r"(?im)^\s*SCREENSHOT[:\s]+([^\n\r]+\.png)\s*$", coder_summary):
                p = m.group(1).strip()
                if p and p not in screenshots:
                    screenshots.append(p)
        except Exception:
            pass
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
            "screenshots": screenshots,
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
            "duration_seconds": round(time.time() - start_time, 2),
            # Shu bitta vazifa bo'yicha to'liq token hisoboti:
            # provayder / model / agent kesimida.
            "token_usage": usage_ledger.task_usage_block(usage_ledger.current_task_id() or ""),
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
                tool_names=["list_dir", "read_file", "execute_python", "run_shell_command",
                            "verify_code_syntax", "http_get", "browser_navigate",
                            "browser_execute_js"],
                max_steps=6, temperature=0.1, sink=qa_result, custom_keys=custom_keys,
            )
        ]
        if security_enabled:
            streams.append(
                self._capture_agent(
                    station="tester", agent_name="Security Auditor", model_id=security_model,
                    role_md=security_md, task=security_task,
                    tool_names=["list_dir", "read_file", "verify_code_syntax",
                                "http_get", "browser_navigate"],
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
