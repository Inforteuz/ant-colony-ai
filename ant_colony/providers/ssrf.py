"""
SSRF himoyasi — foydalanuvchi kiritgan Base URL'lar uchun.

Custom (OpenAI-compatible) va Ollama provayderlarida URL'ni foydalanuvchi beradi.
Tekshiruvsiz bu server ichki tarmog'iga so'rov yuborish (cloud metadata, ichki
admin panellar) imkonini beradi.

Qoidalar:
  * faqat http/https;
  * DNS rezolyutsiyadan keyin IP tekshiriladi (DNS rebinding'ga qarshi);
  * private / loopback / link-local / metadata (169.254.169.254) bloklanadi;
  * mahalliy manzillar faqat ATAYLAB `allow_local=True` bo'lganda ruxsat etiladi.
"""
import ipaddress
import socket
from typing import List, Tuple
from urllib.parse import urlparse

# Cloud metadata xizmatlari — eng muhim blok.
_METADATA_HOSTS = {
    "169.254.169.254",       # AWS / GCP / Azure / OpenStack
    "metadata.google.internal",
    "100.100.100.200",       # Alibaba Cloud
}

ALLOWED_SCHEMES = ("http", "https")


class UrlNotAllowed(ValueError):
    """Base URL xavfsizlik siyosati bo'yicha rad etildi."""


def _resolve_all(host: str, port: int) -> List[ipaddress._BaseAddress]:
    """Hostning barcha IP manzillari (IPv4 va IPv6)."""
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlNotAllowed(f"Хост не резолвится: {host}") from exc

    addrs = []
    for info in infos:
        sockaddr = info[4]
        try:
            addrs.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    if not addrs:
        raise UrlNotAllowed(f"Не удалось определить IP для {host}")
    return addrs


def _is_blocked(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_base_url(base_url: str, *, allow_local: bool = False) -> Tuple[str, List[str]]:
    """
    Base URL'ni tekshiradi va normallashtirilgan ko'rinishini qaytaradi.

    Returns: (normalized_url, resolved_ips)
    Raises:  UrlNotAllowed — siyosat buzilganda.
    """
    raw = (base_url or "").strip()
    if not raw:
        raise UrlNotAllowed("Base URL пуст")

    parsed = urlparse(raw)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UrlNotAllowed("Разрешены только http и https")
    if not parsed.hostname:
        raise UrlNotAllowed("В URL отсутствует хост")
    if parsed.username or parsed.password:
        # user:pass@host — credential URL ichida yashirilishi mumkin.
        raise UrlNotAllowed("Учётные данные внутри URL не допускаются")

    host = parsed.hostname.lower()
    if host in _METADATA_HOSTS:
        raise UrlNotAllowed("Адрес сервиса метаданных заблокирован")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addrs = _resolve_all(host, port)

    for ip in addrs:
        if str(ip) in _METADATA_HOSTS:
            raise UrlNotAllowed("Адрес сервиса метаданных заблокирован")
        if _is_blocked(ip) and not allow_local:
            raise UrlNotAllowed(
                f"Внутренний адрес {ip} заблокирован. Локальные провайдеры "
                f"(например Ollama) требуют явного разрешения."
            )

    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    return normalized, [str(a) for a in addrs]


def is_local_url(base_url: str) -> bool:
    """URL mahalliy (loopback/private) manzilga ishora qiladimi?"""
    try:
        parsed = urlparse((base_url or "").strip())
        if not parsed.hostname:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return any(_is_blocked(ip) for ip in _resolve_all(parsed.hostname, port))
    except Exception:
        return False
