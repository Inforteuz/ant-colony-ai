"""
Normallashtirilgan provayder xatolari.

Har bir provayder o'z formatida xato qaytaradi. Agent runtime ularning
hammasini bilishi shart emas — u faqat quyidagi kodlar bilan ishlaydi va
shu kodga qarab fallback qilish/qilmaslikni hal qiladi.

MUHIM: `safe_message` foydalanuvchiga ko'rsatiladi, shuning uchun undan
har qanday secret olib tashlanadi (redact.py orqali).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ant_colony.providers.redact import redact_text

# --- Xato kodlari ---
INVALID_API_KEY = "INVALID_API_KEY"
INSUFFICIENT_CREDIT = "INSUFFICIENT_CREDIT"
PERMISSION_DENIED = "PERMISSION_DENIED"
RATE_LIMITED = "RATE_LIMITED"
MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
FEATURE_NOT_SUPPORTED = "FEATURE_NOT_SUPPORTED"
PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
NETWORK_ERROR = "NETWORK_ERROR"
TIMEOUT = "TIMEOUT"
INVALID_BASE_URL = "INVALID_BASE_URL"
UNKNOWN_PROVIDER_ERROR = "UNKNOWN_PROVIDER_ERROR"

# Fallback QILINMAYDIGAN kodlar: bular foydalanuvchi konfiguratsiyasidagi
# muammo — boshqa modelga o'tish ularni tuzatmaydi, faqat kvota yoqadi.
NON_RETRYABLE = {
    INVALID_API_KEY,
    PERMISSION_DENIED,
    INVALID_BASE_URL,
    INSUFFICIENT_CREDIT,
}

# Foydalanuvchiga ko'rsatiladigan qisqa tushuntirishlar.
HUMAN_MESSAGES = {
    INVALID_API_KEY: "API-ключ недействителен или отозван. Проверьте ключ в настройках провайдера.",
    INSUFFICIENT_CREDIT: "На счёте провайдера недостаточно средств или исчерпан лимит.",
    PERMISSION_DENIED: "Ключ не имеет доступа к этому ресурсу (проверьте права или регион).",
    RATE_LIMITED: "Превышен лимит запросов. Попробуйте позже или подключите второго провайдера.",
    MODEL_NOT_FOUND: "Модель не найдена. Обновите список моделей — идентификатор мог измениться.",
    FEATURE_NOT_SUPPORTED: "Провайдер не поддерживает эту возможность для выбранной модели.",
    PROVIDER_UNAVAILABLE: "Провайдер временно недоступен.",
    NETWORK_ERROR: "Сетевая ошибка при обращении к провайдеру.",
    TIMEOUT: "Провайдер не ответил вовремя.",
    INVALID_BASE_URL: "Base URL недопустим или заблокирован политикой безопасности.",
    UNKNOWN_PROVIDER_ERROR: "Неизвестная ошибка провайдера.",
}


@dataclass
class ProviderError(Exception):
    """Barcha drayverlar shu turdagi xato qaytaradi."""

    code: str
    provider: str
    status: Optional[int] = None
    safe_message: str = ""
    retryable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.safe_message:
            self.safe_message = HUMAN_MESSAGES.get(self.code, HUMAN_MESSAGES[UNKNOWN_PROVIDER_ERROR])
        # Secret hech qachon xabarga tushmasin.
        self.safe_message = redact_text(self.safe_message)
        self.retryable = self.code not in NON_RETRYABLE and self.retryable
        super().__init__(f"{self.provider}: {self.code} — {self.safe_message}")

    def to_dict(self, *, include_diagnostics: bool = False) -> Dict[str, Any]:
        """
        API javobi uchun ko'rinish.

        Provayderning xom javob tanasi (`body_excerpt`) MIJOZGA YUBORILMAYDI:
        u kalit qoldig'ini yoki ichki tafsilotlarni echo qilishi mumkin.
        U faqat server loglarida (redaktsiya qilingan holda) qoladi.
        """
        payload: Dict[str, Any] = {
            "code": self.code,
            "provider": self.provider,
            "status": self.status,
            "safe_message": self.safe_message,
            "retryable": self.retryable,
        }
        details = dict(self.details)
        if not include_diagnostics:
            details.pop("body_excerpt", None)
        if details:
            payload["details"] = details
        return payload

    def log_line(self) -> str:
        """Server logi uchun to'liq, lekin redaktsiya qilingan satr."""
        excerpt = redact_text(str(self.details.get("body_excerpt", "")))[:200]
        return f"{self.provider} {self.code} status={self.status} {excerpt}"


def normalize_http_status(
    provider: str,
    status: int,
    body: str = "",
    *,
    retry_after: Optional[float] = None,
) -> ProviderError:
    """
    HTTP statusni normallashtirilgan xatoga aylantiradi.

    Provayder javob tanasi (`body`) secret echo qilishi mumkin, shuning uchun u
    hech qachon to'g'ridan-to'g'ri foydalanuvchiga uzatilmaydi — faqat qisqartirilgan,
    redaktsiya qilingan ko'rinishda diagnostikaga qo'shiladi.
    """
    snippet = redact_text((body or "").strip())[:280]

    if status in (401,):
        code, retryable = INVALID_API_KEY, False
    elif status == 402:
        code, retryable = INSUFFICIENT_CREDIT, False
    elif status == 403:
        code, retryable = PERMISSION_DENIED, False
    elif status == 404:
        code, retryable = MODEL_NOT_FOUND, False
    elif status == 408:
        code, retryable = TIMEOUT, True
    elif status == 429:
        code, retryable = RATE_LIMITED, True
    elif status == 529:
        # Anthropic: overloaded — retry/fallback mumkin.
        code, retryable = PROVIDER_UNAVAILABLE, True
    elif 500 <= status < 600:
        code, retryable = PROVIDER_UNAVAILABLE, True
    else:
        code, retryable = UNKNOWN_PROVIDER_ERROR, False

    details: Dict[str, Any] = {}
    if snippet:
        details["body_excerpt"] = snippet
    if retry_after is not None:
        details["retry_after_s"] = retry_after

    return ProviderError(
        code=code, provider=provider, status=status,
        retryable=retryable, details=details,
    )


def normalize_exception(provider: str, exc: BaseException) -> ProviderError:
    """Tarmoq/timeout kabi istisnolarni normallashtiradi."""
    import asyncio

    if isinstance(exc, ProviderError):
        return exc
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return ProviderError(code=TIMEOUT, provider=provider, retryable=True)
    return ProviderError(
        code=NETWORK_ERROR, provider=provider, retryable=True,
        details={"exception": type(exc).__name__},
    )
