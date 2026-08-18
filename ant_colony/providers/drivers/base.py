"""
Driver bazasi: umumiy HTTP qatlami, auth sarlavhalari va model ro'yxati normalizatsiyasi.

Har bir driver bitta simli protokolga xizmat qiladi va bir nechta provayder
uni ulashadi (masalan `openai_chat` — Groq, OpenRouter, Mistral, DeepSeek,
Cerebras, Together AI).
"""
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from ant_colony.providers import errors as E
from ant_colony.providers.registry import (
    AUTH_BEARER, AUTH_GOOG_API_KEY, AUTH_NONE, AUTH_X_API_KEY,
)

# Connection test uchun qisqa timeout (spetsifikatsiya: 10-20s).
TEST_TIMEOUT_S = 15
LIST_TIMEOUT_S = 20


def build_auth_headers(provider_def: Dict[str, Any], api_key: str) -> Dict[str, str]:
    """Provayder auth uslubiga mos sarlavhalar."""
    auth = provider_def.get("auth", AUTH_BEARER)
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    if auth == AUTH_BEARER and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth == AUTH_X_API_KEY and api_key:
        headers["x-api-key"] = api_key
        # Anthropic uchun majburiy.
        version = provider_def.get("anthropic_version")
        if version:
            headers["anthropic-version"] = version
    elif auth == AUTH_GOOG_API_KEY and api_key:
        headers["x-goog-api-key"] = api_key
    elif auth == AUTH_NONE:
        pass

    return headers


def apply_optional_headers(
    headers: Dict[str, str],
    provider_def: Dict[str, Any],
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Ixtiyoriy atribut sarlavhalari (masalan OpenRouter HTTP-Referer / X-Title).

    Bular secret emas — foydalanuvchi/ilova konfiguratsiyasi.
    """
    mapping = provider_def.get("optional_headers") or {}
    meta = metadata or {}
    for header_name, meta_key in mapping.items():
        value = str(meta.get(meta_key, "") or "").strip()
        if value:
            headers[header_name] = value
    return headers


async def request_json(
    provider_id: str,
    method: str,
    url: str,
    *,
    headers: Dict[str, str],
    payload: Optional[Dict[str, Any]] = None,
    timeout_s: int = TEST_TIMEOUT_S,
) -> Tuple[int, Any, Dict[str, str]]:
    """
    HTTP so'rov yuboradi va (status, json_yoki_matn, response_headers) qaytaradi.

    Xatolarni bu yerda ko'tarmaydi — chaqiruvchi statusni normallashtiradi.
    """
    timeout = aiohttp.ClientTimeout(total=timeout_s, sock_connect=min(8, timeout_s))
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, headers=headers, json=payload) as resp:
                text = await resp.text()
                try:
                    data: Any = await resp.json(content_type=None)
                except Exception:
                    data = text
                return resp.status, data, dict(resp.headers)
    except Exception as exc:
        raise E.normalize_exception(provider_id, exc) from exc


def normalize_model_list(provider_id: str, payload: Any) -> List[Dict[str, Any]]:
    """
    Turli provayder javob shakllarini bitta ko'rinishga keltiradi.

    Qo'llab-quvvatlanadigan shakllar:
      * {"data": [{"id": ...}]}          — OpenAI-mos
      * {"models": [{"name": ...}]}      — Gemini, Ollama (/api/tags)
      * [{"id": ...}]                    — ro'yxatning o'zi
    """
    items: List[Any]
    if isinstance(payload, dict):
        items = payload.get("data") or payload.get("models") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    out: List[Dict[str, Any]] = []
    for it in items:
        if isinstance(it, str):
            out.append({"model_id": it, "display_name": it, "raw": {"id": it}})
            continue
        if not isinstance(it, dict):
            continue

        # Gemini: "models/gemini-2.5-flash" -> canonical id shu ko'rinishda qoladi,
        # lekin ko'rsatish uchun qisqartiramiz.
        model_id = (
            it.get("id")
            or it.get("name")
            or it.get("model")
            or it.get("slug")
            or ""
        )
        if not model_id:
            continue

        display = it.get("display_name") or it.get("displayName") or model_id
        if isinstance(model_id, str) and model_id.startswith("models/"):
            display = display.replace("models/", "")

        entry: Dict[str, Any] = {
            "model_id": str(model_id),
            "display_name": str(display),
            "raw": it,
        }

        # Capability'larni FAQAT ishonchli metadatadan olamiz — model nomidan taxmin
        # qilish noto'g'ri natija beradi (spetsifikatsiya talabi).
        caps: Dict[str, Any] = {}
        for key, cap in (
            ("supported_generation_methods", "generation_methods"),
            ("supportedGenerationMethods", "generation_methods"),
            ("context_length", "context_length"),
            ("inputTokenLimit", "context_length"),
            ("max_completion_tokens", "max_output"),
            ("outputTokenLimit", "max_output"),
        ):
            if key in it:
                caps[cap] = it[key]
        if caps:
            entry["capabilities"] = caps

        out.append(entry)

    # Barqaror tartib — UI'da model ro'yxati sakramasin.
    out.sort(key=lambda m: m["model_id"])
    return out


class ProviderDriver:
    """Barcha drayverlar uchun umumiy interfeys."""

    name = "base"

    def __init__(self, provider_id: str, provider_def: Dict[str, Any]) -> None:
        self.provider_id = provider_id
        self.definition = provider_def

    def _url(self, base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}{path}"

    async def test_connection(self, conn: Dict[str, Any]) -> Dict[str, Any]:
        """Kalit/ulanish haqiqiyligini arzon so'rov bilan tekshiradi."""
        raise NotImplementedError

    async def list_models(self, conn: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Provayderdagi mavjud modellar ro'yxati."""
        raise NotImplementedError
