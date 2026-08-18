"""
Provayder ulanishlari uchun saqlash qatlami.

Loyihada ma'lumotlar bazasi yo'q — holat JSON fayllarda saqlanadi. Shuning uchun
BYOK spetsifikatsiyasidagi `provider_connections` / `provider_models` jadvallari
shu faylga moslashtirilgan, lekin maydonlar va semantika saqlangan.

Fayl: data/provider_connections.json (gitignore'da).
Shifrlangan kalit shu faylda yotadi, master kalit esa boshqa joyda —
`ANT_SECRET_KEY` yoki ~/.ant_colony/secret.key.
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ant_colony.config import DATA_DIR
from ant_colony.providers import secrets as secret_service
from ant_colony.providers.redact import mask_key

STORE_FILE: Path = DATA_DIR / "provider_connections.json"

# Model keshi eskirgan deb hisoblanadigan muddat (spetsifikatsiya: 1-24 soat).
MODEL_TTL_S = 6 * 3600

_lock = threading.RLock()


def _now() -> float:
    return time.time()


def _empty_state() -> Dict[str, Any]:
    return {"version": 1, "connections": {}}


def _load() -> Dict[str, Any]:
    if not STORE_FILE.exists():
        return _empty_state()
    try:
        data = json.loads(STORE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "connections" not in data:
            return _empty_state()
        return data
    except Exception:
        # Buzuq fayl butun ilovani to'xtatmasin.
        return _empty_state()


def _invalidate_runtime_cache() -> None:
    """
    Ulanish o'zgargach models_hub keshini tozalaymiz.

    Aks holda yangi/o'chirilgan kalit 30 soniyagacha eski holatda ishlatilardi.
    Import ichkarida — aylanma bog'liqlikni oldini olish uchun.
    """
    try:
        from ant_colony.llm.models_hub import models_hub
        models_hub.invalidate_byok_cache()
    except Exception:
        pass


def _save(state: Dict[str, Any]) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STORE_FILE)  # atomik almashtirish
    try:
        os.chmod(STORE_FILE, 0o600)
    except OSError:
        pass
    _invalidate_runtime_cache()


def public_view(conn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ulanishning API orqali qaytariladigan ko'rinishi.

    KRITIK: bu yerda hech qachon raw kalit bo'lmaydi — faqat maskalangan
    barmoq izi va metadata (spetsifikatsiya: "Read endpoints never return secret").
    """
    return {
        "id": conn["id"],
        "provider": conn["provider"],
        "display_name": conn.get("display_name") or conn["provider"],
        "base_url": conn.get("base_url", ""),
        "has_secret": bool(conn.get("encrypted_api_key")),
        "masked_key": conn.get("masked_key", ""),
        "key_version": (conn.get("encrypted_api_key") or {}).get("key_version", ""),
        "status": conn.get("status", "pending"),
        "last_error_code": conn.get("last_error_code"),
        "last_error_message": conn.get("last_error_message"),
        "last_tested_at": conn.get("last_tested_at"),
        "models_synced_at": conn.get("models_synced_at"),
        "models_count": len(conn.get("models", [])),
        "default_model_id": conn.get("default_model_id"),
        "enabled": conn.get("enabled", True),
        "metadata": conn.get("metadata", {}),
        "created_at": conn.get("created_at"),
        "updated_at": conn.get("updated_at"),
    }


def list_connections(include_models: bool = False) -> List[Dict[str, Any]]:
    with _lock:
        state = _load()
        out = []
        for conn in state["connections"].values():
            view = public_view(conn)
            if include_models:
                view["models"] = conn.get("models", [])
            out.append(view)
        out.sort(key=lambda c: c.get("created_at") or 0)
        return out


def get_connection(conn_id: str) -> Optional[Dict[str, Any]]:
    """Ichki (to'liq) yozuv — faqat server ichida ishlatiladi."""
    with _lock:
        return _load()["connections"].get(conn_id)


def get_by_provider(provider_id: str) -> Optional[Dict[str, Any]]:
    """Provayder bo'yicha birinchi faol ulanish."""
    with _lock:
        for conn in _load()["connections"].values():
            if conn.get("provider") == provider_id and conn.get("enabled", True):
                return conn
    return None


def decrypt_key(conn: Dict[str, Any]) -> str:
    """Ulanish kalitini ochadi (faqat server tomonda chaqiriladi)."""
    envelope = conn.get("encrypted_api_key")
    if not envelope:
        return ""
    return secret_service.decrypt(envelope, aad=conn["id"])


def save_connection(
    *,
    provider: str,
    base_url: str,
    api_key: str,
    display_name: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    models: Optional[List[Dict[str, Any]]] = None,
    default_model_id: Optional[str] = None,
    conn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ulanishni yaratadi yoki yangilaydi.

    Kalit FAQAT muvaffaqiyatli testdan keyin bu yerga keladi (service.py mantiqi),
    va bu yerda darhol shifrlanadi.
    """
    with _lock:
        state = _load()
        now = _now()
        cid = conn_id or str(uuid.uuid4())
        existing = state["connections"].get(cid, {})

        conn: Dict[str, Any] = {
            "id": cid,
            "provider": provider,
            "display_name": display_name or existing.get("display_name") or provider,
            "base_url": base_url,
            "metadata": metadata if metadata is not None else existing.get("metadata", {}),
            "status": "connected",
            "last_error_code": None,
            "last_error_message": None,
            "last_tested_at": now,
            "enabled": existing.get("enabled", True),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }

        if api_key:
            conn["encrypted_api_key"] = secret_service.encrypt(api_key, aad=cid)
            conn["masked_key"] = mask_key(api_key)
        else:
            # Kalit berilmagan (masalan Ollama) yoki eskisi saqlanadi.
            conn["encrypted_api_key"] = existing.get("encrypted_api_key")
            conn["masked_key"] = existing.get("masked_key", "")

        if models is not None:
            conn["models"] = models
            conn["models_synced_at"] = now
        else:
            conn["models"] = existing.get("models", [])
            conn["models_synced_at"] = existing.get("models_synced_at")

        chosen_default = default_model_id or existing.get("default_model_id")
        available = {m["model_id"] for m in conn["models"]}
        # Eski default model provayderdan yo'qolgan bo'lsa — uni saqlab qolmaymiz.
        conn["default_model_id"] = chosen_default if chosen_default in available else (
            next(iter(sorted(available)), None) if available else None
        )

        state["connections"][cid] = conn
        _save(state)
        return conn


def update_models(conn_id: str, models: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Model keshini yangilaydi.

    Eski model darhol o'chirilmaydi — `is_available=false` qilinadi, aks holda
    agentlarning tarixiy konfiguratsiyasi buziladi (spetsifikatsiya talabi).
    """
    with _lock:
        state = _load()
        conn = state["connections"].get(conn_id)
        if not conn:
            return None

        fresh_ids = {m["model_id"] for m in models}
        merged: List[Dict[str, Any]] = []
        for m in models:
            merged.append({**m, "is_available": True})

        for old in conn.get("models", []):
            if old["model_id"] not in fresh_ids:
                merged.append({**old, "is_available": False})

        conn["models"] = merged
        conn["models_synced_at"] = _now()
        conn["updated_at"] = _now()

        if conn.get("default_model_id") not in fresh_ids:
            conn["default_model_id"] = next(iter(sorted(fresh_ids)), None)

        _save(state)
        return conn


def mark_error(conn_id: str, code: str, message: str) -> None:
    """Ulanishni xato holatiga o'tkazadi (kalitga tegmasdan)."""
    with _lock:
        state = _load()
        conn = state["connections"].get(conn_id)
        if not conn:
            return
        conn["status"] = "error"
        conn["last_error_code"] = code
        conn["last_error_message"] = message
        conn["last_tested_at"] = _now()
        conn["updated_at"] = _now()
        _save(state)


def patch_connection(conn_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    """Faqat xavfsiz maydonlarni o'zgartiradi (kalit bu yerda o'zgarmaydi)."""
    allowed = {"display_name", "enabled", "default_model_id", "metadata"}
    with _lock:
        state = _load()
        conn = state["connections"].get(conn_id)
        if not conn:
            return None
        for key, value in fields.items():
            if key in allowed and value is not None:
                conn[key] = value
        conn["updated_at"] = _now()
        _save(state)
        return conn


def delete_connection(conn_id: str) -> bool:
    """
    Ulanishni o'chiradi.

    DIQQAT: bu provayder tomonidagi kalitni BEKOR QILMAYDI — foydalanuvchi
    kalitni provayder konsolida ham o'chirishi kerak. UI shu farqni ko'rsatadi.
    """
    with _lock:
        state = _load()
        if conn_id not in state["connections"]:
            return False
        del state["connections"][conn_id]
        _save(state)
        return True


def models_are_stale(conn: Dict[str, Any]) -> bool:
    synced = conn.get("models_synced_at") or 0
    return (_now() - synced) > MODEL_TTL_S
