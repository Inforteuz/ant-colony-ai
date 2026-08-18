"""
Protokol drayverlari.

Bitta driver bir nechta provayderga xizmat qiladi — 12 provayder uchun 12 ta
nusxa driver yozish shart emas (BYOK spetsifikatsiyasi talabi):

    openai_chat          — Groq, OpenRouter, Mistral, DeepSeek, Cerebras,
                           Together AI, Custom (OpenAI-compatible)
    openai_responses     — OpenAI, xAI
    anthropic_messages   — Anthropic / Claude
    gemini_interactions  — Google Gemini
    cohere_v2            — Cohere
    ollama_native        — Ollama (local)
"""
from typing import Any, Dict, List

from ant_colony.providers import errors as E
from ant_colony.providers.drivers.base import (
    LIST_TIMEOUT_S, TEST_TIMEOUT_S, ProviderDriver, apply_optional_headers,
    build_auth_headers, normalize_model_list, request_json,
)


class _HttpDriver(ProviderDriver):
    """Umumiy REST xatti-harakati: test endpointi + models endpointi."""

    test_method = "GET"

    def _headers(self, conn: Dict[str, Any]) -> Dict[str, str]:
        headers = build_auth_headers(self.definition, conn.get("api_key", ""))
        return apply_optional_headers(headers, self.definition, conn.get("metadata"))

    async def test_connection(self, conn: Dict[str, Any]) -> Dict[str, Any]:
        path = self.definition.get("test_path") or self.definition.get("models_path", "/models")
        method = self.definition.get("test_method", self.test_method)
        url = self._url(conn["base_url"], path)

        status, body, headers = await request_json(
            self.provider_id, method, url,
            headers=self._headers(conn),
            payload={} if method == "POST" else None,
            timeout_s=TEST_TIMEOUT_S,
        )
        if status >= 400:
            raise E.normalize_http_status(
                self.provider_id, status,
                body if isinstance(body, str) else str(body),
                retry_after=_retry_after(headers),
            )
        return {"ok": True, "status": status, "info": _test_info(body)}

    async def list_models(self, conn: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = self._url(conn["base_url"], self.definition.get("models_path", "/models"))
        status, body, headers = await request_json(
            self.provider_id, "GET", url,
            headers=self._headers(conn),
            timeout_s=LIST_TIMEOUT_S,
        )
        if status >= 400:
            raise E.normalize_http_status(
                self.provider_id, status,
                body if isinstance(body, str) else str(body),
                retry_after=_retry_after(headers),
            )
        return normalize_model_list(self.provider_id, body)


def _retry_after(headers: Dict[str, str]) -> float | None:
    raw = (headers or {}).get("Retry-After") or (headers or {}).get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _test_info(body: Any) -> Dict[str, Any]:
    """
    Test javobidan foydali, LEKIN maxfiy bo'lmagan ma'lumotni ajratadi.

    Masalan OpenRouter `/key` limit va kreditni qaytaradi — buni ko'rsatish
    foydalanuvchiga juda foydali. Raw javob hech qachon to'liq uzatilmaydi.
    """
    if not isinstance(body, dict):
        return {}
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    out: Dict[str, Any] = {}
    for key in ("label", "limit", "limit_remaining", "usage", "is_free_tier", "rate_limit"):
        if key in data:
            out[key] = data[key]
    return out


class OpenAIChatDriver(_HttpDriver):
    """OpenAI Chat Completions bilan mos provayderlar."""
    name = "openai_chat"


class OpenAIResponsesDriver(_HttpDriver):
    """Responses API (OpenAI, xAI). Model ro'yxati baribir /models orqali."""
    name = "openai_responses"


class AnthropicMessagesDriver(_HttpDriver):
    """
    Anthropic native Messages API.

    `x-api-key` + `anthropic-version` sarlavhalari majburiy — ular
    registry'dagi auth konfiguratsiyasi orqali qo'shiladi.
    """
    name = "anthropic_messages"


class GeminiInteractionsDriver(_HttpDriver):
    """
    Google Gemini — Interactions API.

    API versiyasi (`v1beta`) registry'da konfiguratsiya sifatida saqlanadi,
    biznes mantiqqa qotirilmaydi.
    """
    name = "gemini_interactions"


class CohereV2Driver(_HttpDriver):
    """
    Cohere v2.

    `POST /v1/check-api-key` — kalit faolligini tekshirish uchun maxsus endpoint,
    shuning uchun test metodi POST.
    """
    name = "cohere_v2"
    test_method = "POST"


class OllamaNativeDriver(_HttpDriver):
    """
    Ollama (local) — API kalit talab qilmaydi.

    `GET /api/tags` 200 qaytarsa, mahalliy Ollama ishlayapti va o'rnatilgan
    modellar ro'yxatini beradi.
    """
    name = "ollama_native"

    async def test_connection(self, conn: Dict[str, Any]) -> Dict[str, Any]:
        result = await super().test_connection(conn)
        models = await self.list_models(conn)
        result["info"] = {"installed_models": len(models)}
        if not models:
            result["warning"] = (
                "Ollama доступен, но модели не установлены. Выполните, например: ollama pull llama3"
            )
        return result


DRIVER_CLASSES = {
    OpenAIChatDriver.name: OpenAIChatDriver,
    OpenAIResponsesDriver.name: OpenAIResponsesDriver,
    AnthropicMessagesDriver.name: AnthropicMessagesDriver,
    GeminiInteractionsDriver.name: GeminiInteractionsDriver,
    CohereV2Driver.name: CohereV2Driver,
    OllamaNativeDriver.name: OllamaNativeDriver,
}


def get_driver(provider_id: str, provider_def: Dict[str, Any]) -> ProviderDriver:
    """Provayder ta'rifidagi `driver` maydoniga mos adapterni qaytaradi."""
    driver_name = provider_def.get("driver", OpenAIChatDriver.name)
    cls = DRIVER_CLASSES.get(driver_name, OpenAIChatDriver)
    return cls(provider_id, provider_def)
