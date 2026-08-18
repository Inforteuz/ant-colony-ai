"""
Configuration and model definitions for Ant Colony AI Platform.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)


def _load_dotenv(path: Path) -> None:
    """
    `.env` faylini muhit o'zgaruvchilariga yuklaydi (tashqi kutubxonasiz).

    MUHIM: ilgari setup sehrgari `.env` faylini YOZARDI, lekin uni hech kim
    O'QIMASDI — serverni qayta ishga tushirgach kalitlar yo'qolardi va ilova
    faqat kodga yozib qo'yilgan zaxira kalitlar hisobiga ishlardi. Endi kalitlar
    haqiqatan ham `.env` dan tiklanadi.

    Tizim muhitida allaqachon mavjud qiymat ustunroq — CI/Docker'da `.env`
    faylni majburan bosib o'tmasligi uchun.
    """
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # Buzuq `.env` butun ilovani to'xtatmasligi kerak.
        pass


_load_dotenv(BASE_DIR / ".env")

# Loyihalar papkasi. Standart — foydalanuvchi uy katalogidagi `AntColonyProjects`.
# Har qanday OS'da ishlaydi; `PROJECTS_BASE_DIR` env orqali o'zgartiriladi.
# (Ilgari bu yerda `/Users/apple/Desktop/04_Loyihalar` qattiq yozilgan edi —
#  boshqa foydalanuvchida ham, Linux/Windows'da ham ishlamasdi.)
_projects_env = os.getenv("PROJECTS_BASE_DIR", "").strip()
PROJECTS_BASE_DIR = Path(_projects_env).expanduser() if _projects_env else (Path.home() / "AntColonyProjects")
try:
    PROJECTS_BASE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# API kalitlari FAQAT muhit o'zgaruvchilaridan o'qiladi (`.env` fayli yoki tizim env).
# Kodda hech qanday kalit saqlanmaydi — `.env.example` dan nusxa oling:
#     cp .env.example .env
# va o'z kalitlaringizni qo'ying. Kamida bitta provayder kaliti kerak.
PROVIDERS = {
    "gemini": {
        "id": "gemini",
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_key": os.getenv("GEMINI_API_KEY", ""),
        "chat_endpoint": "/models",
        "supports_native_tools": True
    },
    "17_wtf": {
        "id": "17_wtf",
        "name": "17.wtf API",
        "base_url": "https://api.17.wtf/v1",
        "default_key": os.getenv("WTF_API_KEY", ""),
        "chat_endpoint": "/chat/completions",
        "messages_endpoint": "/messages",
        "supports_native_tools": True
    },
    "openrouter": {
        "id": "openrouter",
        "name": "OpenRouter.ai",
        "base_url": "https://openrouter.ai/api/v1",
        "default_key": os.getenv("OPENROUTER_API_KEY", ""),
        "chat_endpoint": "/chat/completions",
        "supports_native_tools": True
    },
    "github": {
        "id": "github",
        "name": "GitHub Models",
        "base_url": "https://models.inference.ai.azure.com",
        "default_key": os.getenv("GITHUB_TOKEN", ""),
        "chat_endpoint": "/chat/completions",
        "supports_native_tools": True
    },
    "groq": {
        "id": "groq",
        "name": "Groq Cloud (LPU Ultra-Fast)",
        "base_url": "https://api.groq.com/openai/v1",
        "default_key": os.getenv("GROQ_API_KEY", ""),
        "chat_endpoint": "/chat/completions",
        "supports_native_tools": True
    }
}

# --- Agent xatti-harakati sozlamalari ---
AGENT_CONFIG = {
    # Bitta agent ichida ketma-ket bajarishi mumkin bo'lgan tool qadamlar soni.
    "max_tool_steps": int(os.getenv("AGENT_MAX_TOOL_STEPS", "8")),
    # QA bahosi shu qiymatdan past bo'lsa, kod tuzatish (repair) sikli ishga tushadi.
    "repair_threshold": float(os.getenv("AGENT_REPAIR_THRESHOLD", "80")),
    # Maksimal tuzatish sikllari soni.
    "max_repair_rounds": int(os.getenv("AGENT_MAX_REPAIR_ROUNDS", "2")),
    # LLM chaqiruvi uchun bazaviy timeout (sekund) — max_tokens hisobiga oshiriladi.
    "llm_base_timeout_s": float(os.getenv("AGENT_LLM_BASE_TIMEOUT", "45")),
    "llm_max_timeout_s": float(os.getenv("AGENT_LLM_MAX_TIMEOUT", "210")),
    # Har bir model uchun qayta urinishlar (429/5xx holatlarida).
    "llm_retries_per_model": int(os.getenv("AGENT_LLM_RETRIES", "2")),
    # Model tanlashda o'rganish uchun tasodifiy izlanish ulushi (epsilon-greedy).
    "exploration_rate": float(os.getenv("AGENT_EXPLORATION_RATE", "0.15")),
    # Fon monitoringi oralig'i (sekund). Bepul kvotani tejash uchun uzoq oraliq.
    "health_monitor_interval_s": int(os.getenv("AGENT_HEALTH_INTERVAL", "600")),
    # Bir raundda tekshiriladigan model soni (aylanma navbat bilan).
    "health_monitor_batch": int(os.getenv("AGENT_HEALTH_BATCH", "4")),
    # LLM generation defaults — Setup wizard'dan o'zgartirilishi mumkin.
    "default_temperature": float(os.getenv("AGENT_DEFAULT_TEMPERATURE", "0.2")),
    "default_max_tokens": int(os.getenv("AGENT_DEFAULT_MAX_TOKENS", "8192")),
    # Vision (rasm/video) qo'llab-quvvatlash — global feature flag.
    "enable_vision": os.getenv("AGENT_ENABLE_VISION", "true").lower() in ("true", "1", "yes"),
    # Faqat bepul modellar bilan ishlash rejimi (paid modellar chetlanadi).
    "free_models_only": os.getenv("AGENT_FREE_ONLY", "false").lower() in ("true", "1", "yes"),
}

MODELS_CATALOG = [
    # Google Gemini Models (1M Context)
    {
        "id": "gemini-3.7-flash",
        "provider": "gemini",
        "name": "Gemini 3.7 Flash (1M Context)",
        "context_window": 1048576,
        "max_output": 65536,
        "features": ["1M Context", "Fast Reasoning", "Multimodal", "Code"],
        "supports_reasoning": True,
        "recommended_for": "pm",
        "default_role": "Master Project Manager & Chief Architect",
        "is_free": True
    },
    {
        "id": "gemini-3.6-flash",
        "provider": "gemini",
        "name": "Gemini 3.6 Flash (1M Context)",
        "context_window": 1048576,
        "max_output": 65536,
        "features": ["1M Context", "High Speed", "General"],
        "supports_reasoning": True,
        "recommended_for": "coding",
        "default_role": "Senior Logic Engineer",
        "is_free": True
    },
    {
        "id": "gemini-3.5-flash-lite",
        "provider": "gemini",
        "name": "Gemini 3.5 Flash Lite",
        "context_window": 1048576,
        "max_output": 65536,
        "features": ["1M Context", "Ultra Fast", "Lightweight"],
        "supports_reasoning": False,
        "recommended_for": "fast_tasks",
        "default_role": "Rapid Scripting & QA Tester",
        "is_free": True
    },
    {
        "id": "gemini-2.5-flash",
        "provider": "gemini",
        "name": "Gemini 2.5 Flash",
        "context_window": 1048576,
        "max_output": 65536,
        "features": ["1M Context", "Stable", "General"],
        "supports_reasoning": False,
        "recommended_for": "general",
        "default_role": "Full-Stack Generalist",
        "is_free": True
    },
    # 17.wtf Models
    {
        "id": "posiden/deepseek-v4-flash",
        "provider": "17_wtf",
        "name": "DeepSeek V4 Flash",
        "context_window": 262144,
        "max_output": 262144,
        "features": ["Tools", "Functions", "Reasoning", "Coding"],
        "supports_reasoning": True,
        "recommended_for": "coding",
        "default_role": "Code Architect & Full-Stack Developer",
        "is_free": True
    },
    {
        "id": "posiden/nemotron-3.5-lightning",
        "provider": "17_wtf",
        "name": "Nemotron 3.5 Lightning",
        "context_window": 262144,
        "max_output": 131072,
        "features": ["Ultra Fast", "Tools", "Functions", "Reasoning"],
        "supports_reasoning": True,
        "recommended_for": "fast_tasks",
        "default_role": "Rapid Scripting & Bug Triager",
        "is_free": True
    },
    {
        "id": "posiden/hy3",
        "provider": "17_wtf",
        "name": "HY3 Enterprise",
        "context_window": 268288,
        "max_output": 262144,
        "features": ["Tools", "Functions", "Reasoning"],
        "supports_reasoning": True,
        "recommended_for": "general",
        "default_role": "General Intelligence Coordinator",
        "is_free": True
    },
    {
        "id": "posiden/nemotron-3-ultra",
        "provider": "17_wtf",
        "name": "Nemotron 3 Ultra (1M Context)",
        "context_window": 1048576,
        "max_output": 1048576,
        "features": ["1M Context", "Deep Reasoning", "Tools"],
        "supports_reasoning": True,
        "recommended_for": "large_context",
        "default_role": "Complex System Architect",
        "is_free": True
    },
    # OpenRouter Models
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "provider": "openrouter",
        "name": "Nemotron 3 Nano Omni Reasoning",
        "context_window": 131072,
        "max_output": 32768,
        "features": ["Reasoning Tokens", "Tools", "Fast"],
        "supports_reasoning": True,
        "recommended_for": "reasoning",
        "default_role": "Math & Logic Solver",
        "is_free": True
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "name": "Nemotron 3 Ultra 550B",
        "context_window": 262144,
        "max_output": 65536,
        "features": ["Massive 550B", "Reasoning", "Tools"],
        "supports_reasoning": True,
        "recommended_for": "complex_planning",
        "default_role": "Project Lead & Master Planner",
        "is_free": True
    },
    {
        "id": "cohere/north-mini-code:free",
        "provider": "openrouter",
        "name": "Cohere North Mini Code",
        "context_window": 131072,
        "max_output": 16384,
        "features": ["Specialized Code", "Python/JS", "Tools"],
        "supports_reasoning": False,
        "recommended_for": "coding",
        "default_role": "Code Reviewer & Quality Auditor",
        "is_free": True
    },
    {
        "id": "poolside/laguna-xs-2.1:free",
        "provider": "openrouter",
        "name": "Poolside Laguna XS 2.1",
        "context_window": 65536,
        "max_output": 8192,
        "features": ["Ultra Fast TTFT", "Assistant"],
        "supports_reasoning": False,
        "recommended_for": "fast_tasks",
        "default_role": "Instant Responder & Note Taker",
        "is_free": True
    },
    {
        "id": "dots-studio/dots-3-note-preview:free",
        "provider": "openrouter",
        "name": "Dots 3 Note Preview",
        "context_window": 65536,
        "max_output": 16384,
        "features": ["Note Generation", "Summarization", "Fast"],
        "supports_reasoning": False,
        "recommended_for": "fast_tasks",
        "default_role": "Fast Note Taker & Summarizer",
        "is_free": True
    },
    {
        "id": "liquid/lfm-2.5-2.6b:free",
        "provider": "openrouter",
        "name": "Liquid LFM 2.5 2.6B",
        "context_window": 32768,
        "max_output": 8192,
        "features": ["Liquid State Machine", "Ultra Fast"],
        "supports_reasoning": False,
        "recommended_for": "fast_tasks",
        "default_role": "Micro-Agent & Rapid Triager",
        "is_free": True
    },
    # GitHub Models (Free with GitHub Personal Access Token)
    {
        "id": "gpt-4o",
        "provider": "github",
        "name": "GPT-4o (GitHub Models)",
        "context_window": 128000,
        "max_output": 4096,
        "features": ["OpenAI Flagship", "Vision", "Code", "GitHub Token"],
        "supports_reasoning": True,
        "recommended_for": "coder",
        "default_role": "Full-Stack Engineer & Architect",
        "is_free": True
    },
    {
        "id": "DeepSeek-R1",
        "provider": "github",
        "name": "DeepSeek R1 (GitHub Models)",
        "context_window": 64000,
        "max_output": 8192,
        "features": ["Deep Reasoning", "Math & Logic", "GitHub Token"],
        "supports_reasoning": True,
        "recommended_for": "pm",
        "default_role": "Master Project Manager",
        "is_free": True
    },
    {
        "id": "Meta-Llama-3.3-70B-Instruct",
        "provider": "github",
        "name": "Llama 3.3 70B (GitHub Models)",
        "context_window": 128000,
        "max_output": 4096,
        "features": ["Open Weights", "High Intelligence", "GitHub Token"],
        "supports_reasoning": False,
        "recommended_for": "coder",
        "default_role": "Senior Software Engineer",
        "is_free": True
    },
    {
        "id": "Codestral-2501",
        "provider": "github",
        "name": "Codestral 2501 (GitHub Models)",
        "context_window": 256000,
        "max_output": 8192,
        "features": ["Code Generation", "256K Context", "GitHub Token"],
        "supports_reasoning": False,
        "recommended_for": "coder",
        "default_role": "Code Generation Specialist",
        "is_free": True
    },
    # Groq Cloud Ultra-Fast Models (LPU Speed)
    {
        "id": "groq/compound",
        "provider": "groq",
        "name": "Groq Compound (Ultra-Fast 500+ T/s)",
        "context_window": 128000,
        "max_output": 8192,
        "features": ["Groq LPU Speed", "Multi-Agent Routing", "Low Latency"],
        "supports_reasoning": False,
        "recommended_for": "pm",
        "default_role": "Rapid Project Manager & Coder",
        "is_free": True
    },
    {
        "id": "qwen/qwen3.6-27b",
        "provider": "groq",
        "name": "Qwen 3.6 27B (Groq LPU)",
        "context_window": 32768,
        "max_output": 8192,
        "features": ["Deep Reasoning", "Code & Math", "Groq Speed"],
        "supports_reasoning": True,
        "recommended_for": "coder",
        "default_role": "Full-Stack Algorithm Engineer",
        "is_free": True
    },
    {
        "id": "openai/gpt-oss-120b",
        "provider": "groq",
        "name": "GPT-OSS 120B (Groq LPU)",
        "context_window": 128000,
        "max_output": 8192,
        "features": ["120B Parameter Architecture", "High Intelligence", "Groq Speed"],
        "supports_reasoning": False,
        "recommended_for": "coder",
        "default_role": "Senior System Architect",
        "is_free": True
    }
]

# Workstation definitions matching 3D Hive UI
WORKSTATIONS = {
    "pm": {
        "id": "pm",
        "name": "Центральное управление (PM HQ)",
        "role": "Project Manager & Master Architect",
        "color": "#8b5cf6",
        "default_model": "gemini-3.7-flash"
    },
    "coder": {
        "id": "coder",
        "name": "Инженер-разработчик",
        "role": "Senior Full-Stack & Algorithm Developer",
        "color": "#6366f1",
        "default_model": "posiden/deepseek-v4-flash"
    },
    "tester": {
        "id": "tester",
        "name": "Инженер тестирования (QA)",
        "role": "QA Engineer & Test Suite Runner",
        "color": "#06b6d4",
        "default_model": "posiden/nemotron-3.5-lightning"
    },
    "researcher": {
        "id": "researcher",
        "name": "Аналитик данных",
        "role": "Data Analyst & Web Researcher",
        "color": "#10b981",
        "default_model": "gemini-3.5-flash-lite"
    },
    "designer": {
        "id": "designer",
        "name": "Дизайнер UI/UX",
        "role": "Frontend Architect & UI/UX Specialist",
        "color": "#ec4899",
        "default_model": "posiden/deepseek-v4-flash"
    },
    "deployer": {
        "id": "deployer",
        "name": "Инженер DevOps",
        "role": "DevOps & Workspace Artifacts Packager",
        "color": "#f97316",
        "default_model": "cohere/north-mini-code:free"
    },
    "monitor": {
        "id": "monitor",
        "name": "Аудит безопасности",
        "role": "System Health & Performance Watcher",
        "color": "#f59e0b",
        "default_model": "poolside/laguna-xs-2.1:free"
    }
}
