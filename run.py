#!/usr/bin/env python3
"""
Ant Colony AI — entrypoint.

Ishga tushirish:
    python run.py

Sozlash (.env yoki muhit o'zgaruvchilari):
    ANT_HOST   (default 127.0.0.1)  — tarmoqqa ochish xavfli, README ga qarang
    ANT_PORT   (default 8080)
    ANT_RELOAD (default 0)          — ishlab chiqish uchun avtomatik qayta yuklash
"""
import os
import sys
from pathlib import Path

# Repo ildizini import yo'liga qo'shamiz, shunda `python run.py` istalgan
# katalogdan ishlaydi (masalan `python /path/to/repo/run.py`).
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    import uvicorn

    # Standart holatda faqat mahalliy interfeys. Platformada shell buyruqlarini
    # bajaruvchi endpoint bor — uni tarmoqqa ochish autentifikatsiyasiz RCE demakdir.
    host = os.getenv("ANT_HOST", "127.0.0.1")
    port = int(os.getenv("ANT_PORT", "8080"))
    reload_enabled = os.getenv("ANT_RELOAD", "0").lower() in ("1", "true", "yes")

    if host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"\n[OGOHLANTIRISH] Server {host} manzilida tinglaydi — tarmoqdagi har kim "
            f"terminal endpointi orqali buyruq bajara oladi.\n"
            f"Buni faqat ishonchli, izolyatsiyalangan tarmoqda qiling.\n"
        )

    uvicorn.run("ant_colony.server:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
