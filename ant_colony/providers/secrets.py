"""
Credential shifrlash (encryption at rest) — AES-256-GCM envelope.

BYOK talabi: API kalit diskda ochiq saqlanmaydi va shifrlash kaliti ma'lumot
bilan bir joyda turmaydi.

Master kalit manbai (ustuvorlik tartibida):
  1. `ANT_SECRET_KEY` muhit o'zgaruvchisi — production uchun to'g'ri yo'l
     (KMS/Vault'dan yetkazing).
  2. `ANT_SECRET_KEY_FILE` — kalit yozilgan fayl yo'li.
  3. Mahalliy avtomatik kalit `~/.ant_colony/secret.key` (0600) — bitta
     mashinadagi shaxsiy o'rnatish uchun qulaylik. Bu holat ochiq
     ogohlantiriladi, chunki himoya faqat OS fayl ruxsatlariga tayanadi.
"""
import base64
import os
import stat
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_VERSION = "v1"
_NONCE_BYTES = 12
_KEY_BYTES = 32  # AES-256

_cached_key: Optional[bytes] = None
_key_source: str = "unknown"


def _local_key_path() -> Path:
    return Path.home() / ".ant_colony" / "secret.key"


def _load_or_create_local_key() -> bytes:
    path = _local_key_path()
    if path.exists():
        raw = path.read_bytes().strip()
        try:
            key = base64.urlsafe_b64decode(raw)
        except Exception as exc:
            raise RuntimeError(f"Повреждён локальный ключ шифрования: {path}") from exc
        if len(key) != _KEY_BYTES:
            raise RuntimeError(f"Локальный ключ должен быть {_KEY_BYTES} байт: {path}")
        return key

    key = AESGCM.generate_key(bit_length=256)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.urlsafe_b64encode(key))
    # Faqat egasi o'qiy olsin.
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return key


def get_master_key() -> bytes:
    """Master kalitni oladi (bir marta yuklab, keshlaydi)."""
    global _cached_key, _key_source
    if _cached_key is not None:
        return _cached_key

    env_key = os.getenv("ANT_SECRET_KEY", "").strip()
    if env_key:
        try:
            key = base64.urlsafe_b64decode(env_key)
        except Exception as exc:
            raise RuntimeError("ANT_SECRET_KEY base64 formatida bo'lishi kerak") from exc
        if len(key) != _KEY_BYTES:
            raise RuntimeError(f"ANT_SECRET_KEY {_KEY_BYTES} bayt bo'lishi kerak (base64)")
        _cached_key, _key_source = key, "env"
        return key

    key_file = os.getenv("ANT_SECRET_KEY_FILE", "").strip()
    if key_file:
        raw = Path(key_file).read_bytes().strip()
        key = base64.urlsafe_b64decode(raw)
        if len(key) != _KEY_BYTES:
            raise RuntimeError(f"{key_file}: kalit {_KEY_BYTES} bayt bo'lishi kerak")
        _cached_key, _key_source = key, "file"
        return key

    _cached_key, _key_source = _load_or_create_local_key(), "local"
    return _cached_key


def key_source() -> str:
    """Master kalit qayerdan olingani ('env' | 'file' | 'local') — diagnostika uchun."""
    get_master_key()
    return _key_source


def generate_master_key() -> str:
    """Yangi master kalit (base64) — `ANT_SECRET_KEY` uchun."""
    return base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode()


def encrypt(plaintext: str, *, aad: str = "") -> dict:
    """
    Matnni shifrlaydi.

    `aad` (additional authenticated data) — masalan connection id. Bu ciphertext'ni
    boshqa yozuvga ko'chirib qo'yishdan himoya qiladi: aad mos kelmasa deshifrlash
    muvaffaqiyatsiz bo'ladi.
    """
    if plaintext is None:
        plaintext = ""
    aesgcm = AESGCM(get_master_key())
    nonce = os.urandom(_NONCE_BYTES)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad.encode("utf-8") if aad else None)
    return {
        "ciphertext": base64.b64encode(ct).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "key_version": KEY_VERSION,
    }


def decrypt(envelope: dict, *, aad: str = "") -> str:
    """Shifrlangan qiymatni ochadi. Xato bo'lsa ValueError."""
    if not envelope or not envelope.get("ciphertext"):
        return ""
    try:
        aesgcm = AESGCM(get_master_key())
        ct = base64.b64decode(envelope["ciphertext"])
        nonce = base64.b64decode(envelope["nonce"])
        raw = aesgcm.decrypt(nonce, ct, aad.encode("utf-8") if aad else None)
        return raw.decode("utf-8")
    except Exception as exc:
        # Sabab: master kalit almashgan yoki yozuv buzilgan.
        raise ValueError(
            "Не удалось расшифровать credential. Возможно, изменился ключ шифрования "
            "(ANT_SECRET_KEY). Переподключите провайдера."
        ) from exc
