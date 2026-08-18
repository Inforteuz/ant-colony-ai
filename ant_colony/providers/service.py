"""
Provayder servisi — BYOK oqimining biznes mantiqi.

Spetsifikatsiyadagi `testAndSave` algoritmi:
    1) kirishni tekshirish (SSRF, majburiy maydonlar)
    2) arzon auth/model testi
    3) FAQAT test muvaffaqiyatli bo'lsa — shifrlab saqlash
    4) model katalogini sinxronlash

Muvaffaqiyatsiz kalit hech qachon diskka yozilmaydi.
"""
import logging
from typing import Any, Dict, List, Optional

from ant_colony.providers import errors as E
from ant_colony.providers import store
from ant_colony.providers.drivers.generic import get_driver
from ant_colony.providers.redact import mask_key, redact_text
from ant_colony.providers.registry import get_provider, resolve_base_url
from ant_colony.providers.ssrf import UrlNotAllowed, validate_base_url

logger = logging.getLogger("ant.providers")


class ProviderValidationError(ValueError):
    """Kirish ma'lumotlari noto'g'ri (foydalanuvchiga ko'rsatiladi)."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message)
        self.code = code


def _build_candidate(
    provider_id: str,
    api_key: str,
    base_url: str,
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Vaqtinchalik ("ephemeral") ulanish obyekti — hali saqlanmagan.

    Test aynan shu obyekt bilan bajariladi, shuning uchun noto'g'ri kalit
    diskka umuman tushmaydi.
    """
    provider_def = get_provider(provider_id)
    if not provider_def:
        raise ProviderValidationError(f"Неизвестный провайдер: {provider_id}", "UNKNOWN_PROVIDER")

    key = (api_key or "").strip()
    if provider_def.get("key_required") and not key:
        raise ProviderValidationError("API-ключ обязателен для этого провайдера", "MISSING_KEY")

    resolved = resolve_base_url(provider_id, base_url)
    if not resolved:
        raise ProviderValidationError("Base URL обязателен", "MISSING_BASE_URL")

    # SSRF: foydalanuvchi URL bergan holatlarda majburiy tekshiruv.
    allow_local = bool(provider_def.get("allow_local"))
    try:
        resolved, _ips = validate_base_url(resolved, allow_local=allow_local)
    except UrlNotAllowed as exc:
        raise ProviderValidationError(str(exc), E.INVALID_BASE_URL) from exc

    return {
        "id": "ephemeral",
        "provider": provider_id,
        "base_url": resolved,
        "api_key": key,
        "metadata": metadata or {},
    }


async def test_connection(
    provider_id: str,
    api_key: str = "",
    base_url: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Ulanishni tekshiradi — hech narsa saqlamaydi."""
    candidate = _build_candidate(provider_id, api_key, base_url, metadata)
    provider_def = get_provider(provider_id)
    driver = get_driver(provider_id, provider_def)

    try:
        result = await driver.test_connection(candidate)
    except E.ProviderError as err:
        # To'liq diagnostika faqat server logida qoladi.
        logger.warning("Provider test failed: %s", err.log_line())
        return {"ok": False, "error": err.to_dict()}

    return {
        "ok": True,
        "provider": provider_id,
        "base_url": candidate["base_url"],
        "masked_key": mask_key(candidate["api_key"]),
        "info": result.get("info", {}),
        "warning": result.get("warning"),
    }


async def test_and_save(
    provider_id: str,
    api_key: str = "",
    base_url: str = "",
    display_name: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    default_model_id: Optional[str] = None,
    conn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    To'liq oqim: tekshirish -> test -> model sinxronizatsiyasi -> shifrlab saqlash.

    Muvaffaqiyatsiz bo'lsa hech narsa yozilmaydi va raw kalit qaytarilmaydi.
    """
    candidate = _build_candidate(provider_id, api_key, base_url, metadata)
    provider_def = get_provider(provider_id)
    driver = get_driver(provider_id, provider_def)

    # 1) Arzon auth testi
    try:
        await driver.test_connection(candidate)
    except E.ProviderError as err:
        return {"ok": False, "error": err.to_dict()}

    # 2) Model katalogi
    models: List[Dict[str, Any]] = []
    models_warning = None
    try:
        models = await driver.list_models(candidate)
    except E.ProviderError as err:
        # Test o'tgan, lekin model ro'yxati olinmadi — ulanishni baribir saqlaymiz
        # va foydalanuvchini ogohlantiramiz (keyin "Sync models" bilan qayta urinadi).
        models_warning = err.safe_message

    # 3) Shifrlab saqlash — faqat shu bosqichda
    conn = store.save_connection(
        provider=provider_id,
        base_url=candidate["base_url"],
        api_key=candidate["api_key"],
        display_name=display_name,
        metadata=candidate["metadata"],
        models=[{**m, "is_available": True} for m in models],
        default_model_id=default_model_id,
        conn_id=conn_id,
    )

    return {
        "ok": True,
        "connection": store.public_view(conn),
        "models": conn.get("models", []),
        "warning": models_warning,
    }


async def sync_models(conn_id: str) -> Dict[str, Any]:
    """Saqlangan ulanish uchun model katalogini yangilaydi."""
    conn = store.get_connection(conn_id)
    if not conn:
        raise ProviderValidationError("Подключение не найдено", "NOT_FOUND")

    provider_def = get_provider(conn["provider"])
    if not provider_def:
        raise ProviderValidationError("Провайдер больше не поддерживается", "UNKNOWN_PROVIDER")

    try:
        api_key = store.decrypt_key(conn)
    except ValueError as exc:
        store.mark_error(conn_id, "DECRYPT_FAILED", str(exc))
        return {"ok": False, "error": {"code": "DECRYPT_FAILED", "safe_message": str(exc)}}

    driver = get_driver(conn["provider"], provider_def)
    runtime_conn = {**conn, "api_key": api_key}

    try:
        models = await driver.list_models(runtime_conn)
    except E.ProviderError as err:
        store.mark_error(conn_id, err.code, err.safe_message)
        return {"ok": False, "error": err.to_dict()}

    updated = store.update_models(conn_id, models)
    return {
        "ok": True,
        "connection": store.public_view(updated),
        "models": updated.get("models", []),
    }


async def retest(conn_id: str) -> Dict[str, Any]:
    """Saqlangan ulanishni qayta tekshiradi (kalit almashtirilmaydi)."""
    conn = store.get_connection(conn_id)
    if not conn:
        raise ProviderValidationError("Подключение не найдено", "NOT_FOUND")

    provider_def = get_provider(conn["provider"])
    try:
        api_key = store.decrypt_key(conn)
    except ValueError as exc:
        store.mark_error(conn_id, "DECRYPT_FAILED", str(exc))
        return {"ok": False, "error": {"code": "DECRYPT_FAILED", "safe_message": str(exc)}}

    driver = get_driver(conn["provider"], provider_def)
    try:
        result = await driver.test_connection({**conn, "api_key": api_key})
    except E.ProviderError as err:
        store.mark_error(conn_id, err.code, err.safe_message)
        return {"ok": False, "error": err.to_dict()}

    store.patch_connection(conn_id)  # updated_at yangilanadi
    refreshed = store.get_connection(conn_id) or conn
    refreshed["status"] = "connected"
    refreshed["last_error_code"] = None
    refreshed["last_error_message"] = None
    store.save_connection(
        provider=refreshed["provider"],
        base_url=refreshed["base_url"],
        api_key="",  # mavjud kalit saqlanadi
        display_name=refreshed.get("display_name", ""),
        metadata=refreshed.get("metadata", {}),
        conn_id=conn_id,
    )
    return {"ok": True, "info": result.get("info", {}), "connection": store.public_view(refreshed)}


def runtime_credentials(provider_id: str) -> Optional[Dict[str, Any]]:
    """
    Agent runtime uchun: provayder bo'yicha ishlaydigan credential.

    Bu yagona joy bo'lib, u orqali kalit deshifrlanadi — boshqa modullar
    shifrlangan qiymatga umuman tegmaydi.
    """
    conn = store.get_by_provider(provider_id)
    if not conn or conn.get("status") != "connected":
        return None
    try:
        api_key = store.decrypt_key(conn)
    except ValueError as exc:
        logger.warning("Credential decrypt failed for %s: %s", provider_id, redact_text(str(exc)))
        return None
    return {
        "connection_id": conn["id"],
        "provider": provider_id,
        "api_key": api_key,
        "base_url": conn.get("base_url", ""),
        "default_model_id": conn.get("default_model_id"),
        "metadata": conn.get("metadata", {}),
    }


def connected_models() -> List[Dict[str, Any]]:
    """
    Barcha ulangan provayderlarning mavjud modellari — model tanlash UI'si uchun.
    """
    out: List[Dict[str, Any]] = []
    for view in store.list_connections(include_models=True):
        if not view.get("enabled") or view.get("status") != "connected":
            continue
        for m in view.get("models", []):
            if not m.get("is_available", True):
                continue
            out.append({
                "connection_id": view["id"],
                "provider": view["provider"],
                "provider_label": view["display_name"],
                "model_id": m["model_id"],
                "display_name": m.get("display_name", m["model_id"]),
            })
    return out
