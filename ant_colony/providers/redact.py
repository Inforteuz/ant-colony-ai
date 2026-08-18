"""
Secret redaktsiyasi — loglar, xato xabarlari va API javoblari uchun.

BYOK spetsifikatsiyasining "non-negotiable" talabi: raw API key hech qachon
logga, konsolga, xato xabariga yoki frontend javobiga tushmasligi kerak.
"""
import re
from typing import Any, Dict, Iterable

# Ma'lum provayder kalit naqshlari. Ro'yxat to'liq bo'lishi shart emas —
# `mask_key()` va header allowlist asosiy himoya, bu qo'shimcha qatlam.
_SECRET_PATTERNS = [
    re.compile(r"\bsk-or-v1-[A-Za-z0-9]{16,}\b"),      # OpenRouter
    re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{16,}\b"),     # Anthropic
    re.compile(r"\bgsk_[A-Za-z0-9]{16,}\b"),           # Groq
    re.compile(r"\bcsk-[A-Za-z0-9\-_]{16,}\b"),        # Cerebras
    re.compile(r"\bxai-[A-Za-z0-9\-_]{16,}\b"),        # xAI
    re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}\b"),        # Google
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),           # GitHub
    re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),            # OpenAI va umumiy
]

# So'rov/javob sarlavhalaridan olib tashlanadigan maydonlar.
SENSITIVE_HEADERS = {
    "authorization", "x-api-key", "x-goog-api-key", "api-key",
    "proxy-authorization", "cookie", "set-cookie",
}

REDACTED = "***REDACTED***"


def redact_text(text: str) -> str:
    """Matndan ma'lum kalit naqshlarini olib tashlaydi."""
    if not text:
        return text
    out = str(text)
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def redact_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """Sarlavhalardagi credentiallarni maskalaydi (logga yozishdan oldin)."""
    return {
        k: (REDACTED if k.lower() in SENSITIVE_HEADERS else redact_text(str(v)))
        for k, v in (headers or {}).items()
    }


def mask_key(api_key: str) -> str:
    """
    Kalitning ko'rsatish uchun xavfsiz "barmoq izi": `sk-...ABCD`.

    UI faqat shu qiymatni ko'radi; raw kalit backenddan hech qachon chiqmaydi.
    """
    key = (api_key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    prefix = key[:3]
    suffix = key[-4:]
    return f"{prefix}...{suffix}"


def redact_mapping(data: Dict[str, Any], secret_keys: Iterable[str] = ()) -> Dict[str, Any]:
    """Lug'atdagi nomlangan maydonlarni va matn ichidagi kalitlarni tozalaydi."""
    secret_keys = {k.lower() for k in secret_keys} | {
        "api_key", "apikey", "key", "secret", "token", "encrypted_api_key",
    }
    out: Dict[str, Any] = {}
    for k, v in (data or {}).items():
        if k.lower() in secret_keys:
            out[k] = REDACTED
        elif isinstance(v, str):
            out[k] = redact_text(v)
        elif isinstance(v, dict):
            out[k] = redact_mapping(v, secret_keys)
        else:
            out[k] = v
    return out
