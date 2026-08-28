"""
BYOK provider registry — routing va konfiguratsiya uchun yagona haqiqat manbai.

Muhim qoida (BYOK spetsifikatsiyasidan): registry — marshrutlash va konfiguratsiya,
driver — protokol tarjimasi, secrets — credential xavfsizligi, agent runtime —
biznes mantiq. Bu qatlamlarni bir-biriga aralashtirmaslik kerak.

Model ID'lari BU YERDA qattiq yozilmaydi: har bir provayderning `models_path`
endpointi orqali dinamik sinxronlanadi va keshlanadi.
"""
from typing import Any, Dict, List, Optional

# Driver — bir nechta provayderga xizmat qiluvchi protokol adapteri.
DRIVER_OPENAI_CHAT = "openai_chat"
DRIVER_OPENAI_RESPONSES = "openai_responses"
DRIVER_ANTHROPIC_MESSAGES = "anthropic_messages"
DRIVER_GEMINI_INTERACTIONS = "gemini_interactions"
DRIVER_COHERE_V2 = "cohere_v2"
DRIVER_OLLAMA_NATIVE = "ollama_native"

# Auth uslublari — driver emas, registry darajasidagi konfiguratsiya.
AUTH_BEARER = "bearer"            # Authorization: Bearer <key>
AUTH_X_API_KEY = "x_api_key"      # x-api-key: <key>  (+ anthropic-version)
AUTH_GOOG_API_KEY = "goog_api_key"  # x-goog-api-key: <key>
AUTH_NONE = "none"                # local (Ollama)

CUSTOM_PROVIDER_ID = "custom_openai"


PROVIDER_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.openai.com/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "sk-...",
        "console_url": "https://platform.openai.com/api-keys",
        "docs_url": "https://developers.openai.com/api/docs/quickstart",
        "notes": "Chat Completions API — runtime ham shu endpoint orqali ishlaydi (birlashtirilgan).",
    },
    "anthropic": {
        "label": "Anthropic / Claude",
        "driver": DRIVER_ANTHROPIC_MESSAGES,
        "base_url": "https://api.anthropic.com",
        "models_path": "/v1/models",
        "generate_path": "/v1/messages",
        "test_path": "/v1/models",
        "auth": AUTH_X_API_KEY,
        "anthropic_version": "2023-06-01",
        "key_required": True,
        "key_hint": "sk-ant-...",
        "console_url": "https://platform.claude.com/docs/en/get-api-key",
        "docs_url": "https://platform.claude.com/docs/en/api/messages",
        "notes": "Native Messages API — OpenAI Chat sxemasidan farq qiladi, alohida driver.",
    },
    "gemini": {
        "label": "Google Gemini",
        "driver": DRIVER_GEMINI_INTERACTIONS,
        "base_url": "https://generativelanguage.googleapis.com",
        "api_version": "v1beta",
        "models_path": "/v1beta/models",
        "generate_path": "/v1beta/interactions",
        "test_path": "/v1beta/models",
        "auth": AUTH_GOOG_API_KEY,
        "key_required": True,
        "key_hint": "AIzaSy... yoki auth key",
        "console_url": "https://aistudio.google.com/apikey",
        "docs_url": "https://ai.google.dev/gemini-api/docs/interactions-overview",
        "notes": (
            "Google 2026-yil sentabrdan eski Standard kalitlarni rad etishini e'lon qilgan — "
            "AI Studio'da YANGI auth key yarating."
        ),
    },
    "groq": {
        "label": "Groq Cloud",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.groq.com/openai/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "gsk_...",
        "console_url": "https://console.groq.com/keys",
        "docs_url": "https://console.groq.com/docs/openai",
        "notes": "OpenAI-mos; Responses endpointi beta — barqarorlik uchun Chat Completions.",
    },
    "b_ai": {
        "label": "b.ai services",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.b.ai/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "sk-... (b.ai dan olingan)",
        "console_url": "https://b.ai",
        "docs_url": "https://b.ai",
        "notes": (
            "OpenAI-mos API. 42 ta model: claude-*, gpt-5.*, gemini-3.*, "
            "deepseek-v4-*, hy3, qwen3.8-*, glm-5.*, kimi-k*, minimax-m*. "
            "17.wtf dagi bir xil modellarga qaraganda sezilarli tez "
            "(o'lchov 2026-08-25: hy3 2.2s vs 17.0s)."
        ),
    },
    "17_wtf": {
        "label": "17.wtf API",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.17.wtf/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "sk-... (17.wtf dan olingan)",
        "console_url": "https://17.wtf",
        "docs_url": "https://17.wtf",
        "notes": (
            "OpenAI-mos API (chat/completions). Bir nechta foydalanuvchi (posiden, "
            "elon, zeus ...) taqdim etgan modellar, jumladan bir qancha mutlaqo "
            "tekin modellar: posiden/deepseek-v4-flash, posiden/hy3, "
            "posiden/nemotron-3.5-lightning, posiden/nemotron-3-ultra va "
            "elon/grok-4.5-free."
        ),
    },
    "openrouter": {
        "label": "OpenRouter",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://openrouter.ai/api/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        # /key endpointi kalitni VA limit/kreditni tekshiradi — kuchliroq test.
        "test_path": "/key",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "sk-or-v1-...",
        "console_url": "https://openrouter.ai/keys",
        "docs_url": "https://openrouter.ai/docs/api_reference/authentication",
        "optional_headers": {"HTTP-Referer": "app_url", "X-OpenRouter-Title": "app_title"},
        "notes": "Ko'p provayderni bitta OpenAI-mos sxemaga normallashtiradi.",
    },
    "alibaba_model_studio": {
        "label": "Alibaba Cloud Model Studio",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "Pay-as-you-go Workspace API key",
        "requires_base_url": True,
        "console_url": "",
        "docs_url": "https://help.aliyun.com/en/model-studio/base-url",
        "notes": (
            "OpenAI-mos pay-as-you-go Workspace endpointini kiriting. Token Plan "
            "endpointi va uning kaliti backend/server uchun emas, faqat interaktiv "
            "coding tool'lari uchun; bu ulanishda ishlatilmaydi."
        ),
    },
    "alibaba_token_plan": {
        "label": "Alibaba Cloud Token Plan",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "Token Plan API key (sk-sp-...)",
        "console_url": "",
        "docs_url": "https://help.aliyun.com/en/model-studio/token-plan-personal-quick-start",
        "notes": "OpenAI-compatible Token Plan. Interaktiv agent vazifalari uchun; kalit faqat lokal credential store'da saqlanadi.",
    },
    "mistral": {
        "label": "Mistral AI",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.mistral.ai/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "...",
        "console_url": "https://console.mistral.ai/api-keys",
        "docs_url": "https://docs.mistral.ai/api/endpoint/chat",
        "notes": "Kalitlarga muddat/rotatsiya berish mumkin.",
    },
    "deepseek": {
        "label": "DeepSeek",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.deepseek.com",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "sk-...",
        "console_url": "https://platform.deepseek.com/api_keys",
        "docs_url": "https://api-docs.deepseek.com/",
        "notes": (
            "Eski `deepseek-chat` / `deepseek-reasoner` taxalluslari 2026-07-24 dan keyin "
            "ishlamaydi — model ro'yxatini API'dan oling, kodga yozmang."
        ),
    },
    "xai": {
        "label": "xAI (Grok)",
        "driver": DRIVER_OPENAI_RESPONSES,
        "base_url": "https://api.x.ai/v1",
        "models_path": "/models",
        "generate_path": "/responses",
        "test_path": "/api-key",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "xai-...",
        "console_url": "https://console.x.ai/",
        "docs_url": "https://docs.x.ai/developers/rest-api-reference/inference",
        "notes": "Responses API afzal; `/v1/api-key` kalit haqida ma'lumot beradi.",
    },
    "cerebras": {
        "label": "Cerebras",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.cerebras.ai/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "csk-...",
        "console_url": "https://cloud.cerebras.ai/",
        "docs_url": "https://inference-docs.cerebras.ai/resources/openai",
        "notes": "Rasmiy hujjat kalitni brauzer/mobil kodda oshkor qilmaslikni talab qiladi.",
    },
    "cohere": {
        "label": "Cohere",
        "driver": DRIVER_COHERE_V2,
        "base_url": "https://api.cohere.com",
        "models_path": "/v1/models",
        "generate_path": "/v2/chat",
        # Maxsus validatsiya endpointi — eng ishonchli test.
        "test_path": "/v1/check-api-key",
        "test_method": "POST",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "...",
        "console_url": "https://dashboard.cohere.com/api-keys",
        "docs_url": "https://docs.cohere.com/reference/chat",
        "notes": "Native v2 Chat — funksional paritet uchun alohida driver.",
    },
    "together": {
        "label": "Together AI",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "https://api.together.ai/v1",
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": True,
        "key_hint": "...",
        "console_url": "https://api.together.ai/settings/api-keys",
        "docs_url": "https://docs.together.ai/docs/api-keys-authentication",
        "notes": "Project-scoped kalitlar afzal (eski organization kalitlari emas).",
    },
    "ollama": {
        "label": "Ollama (local)",
        "driver": DRIVER_OLLAMA_NATIVE,
        "base_url": "http://localhost:11434",
        "models_path": "/api/tags",
        "generate_path": "/api/chat",
        "test_path": "/api/tags",
        "auth": AUTH_NONE,
        "key_required": False,
        "allow_local": True,
        "console_url": "https://ollama.com/download",
        "docs_url": "https://docs.ollama.com/api/chat",
        "notes": (
            "Mahalliy rejim. Server boshqa mashinada bo'lsa `localhost` foydalanuvchi "
            "kompyuteriga emas, serverga ishora qiladi."
        ),
    },
    CUSTOM_PROVIDER_ID: {
        "label": "Custom (OpenAI-compatible)",
        "driver": DRIVER_OPENAI_CHAT,
        "base_url": "",  # foydalanuvchi kiritadi
        "models_path": "/models",
        "generate_path": "/chat/completions",
        "test_path": "/models",
        "auth": AUTH_BEARER,
        "key_required": False,
        "requires_base_url": True,
        "console_url": "",
        "docs_url": "",
        "notes": (
            "vLLM, LM Studio, proxy yoki boshqa OpenAI-mos endpoint. Base URL "
            "foydalanuvchidan olinadi, shuning uchun SSRF himoyasi majburiy."
        ),
    },
}

# UI ro'yxatida ko'rsatiladigan tartib (mashhurlik/qulaylik bo'yicha).
PROVIDER_ORDER: List[str] = [
    "openai", "anthropic", "gemini", "groq", "openrouter", "alibaba_token_plan", "alibaba_model_studio", "b_ai", "17_wtf", "mistral",
    "deepseek", "xai", "cerebras", "cohere", "together", "ollama",
    CUSTOM_PROVIDER_ID,
]


def get_provider(provider_id: str) -> Optional[Dict[str, Any]]:
    """Provayder ta'rifini qaytaradi (topilmasa None)."""
    return PROVIDER_DEFINITIONS.get(provider_id)


def list_providers() -> List[Dict[str, Any]]:
    """
    UI uchun provayderlar katalogi.

    DIQQAT: bu javobda hech qanday secret bo'lmaydi — faqat ommaviy metadata.
    """
    out = []
    for pid in PROVIDER_ORDER:
        d = PROVIDER_DEFINITIONS.get(pid)
        if not d:
            continue
        out.append({
            "id": pid,
            "label": d["label"],
            "driver": d["driver"],
            "base_url": d["base_url"],
            "key_required": d["key_required"],
            "key_hint": d.get("key_hint", ""),
            "requires_base_url": d.get("requires_base_url", False),
            "allow_local": d.get("allow_local", False),
            "console_url": d.get("console_url", ""),
            "docs_url": d.get("docs_url", ""),
            "notes": d.get("notes", ""),
        })
    return out


def resolve_base_url(provider_id: str, custom_base_url: str = "") -> str:
    """
    Amaldagi base URL: faqat Custom va Ollama uchun foydalanuvchi qiymati ustun.

    Boshqa provayderlarda base URL registrydan olinadi — aks holda foydalanuvchi
    kiritgan URL orqali kalit begona hostga yuborilishi mumkin edi.
    """
    d = PROVIDER_DEFINITIONS.get(provider_id) or {}
    user_override_allowed = d.get("requires_base_url") or d.get("allow_local")
    if user_override_allowed and custom_base_url.strip():
        return custom_base_url.strip().rstrip("/")
    return str(d.get("base_url", "")).rstrip("/")
