"""
Workspace Janitor — bo'sh yoki tashlab ketilgan loyiha papkalarini avtomatik tozalaydi.

Muammo: AI agent yangi loyiha uchun papka ochadi, lekin biror sabab bilan (LLM xatosi,
rate limit, bekor qilingan orkestratsiya) unga fayl yozilmasdan qoladi. Vaqt o'tishi
bilan `04_Loyihalar` ichida o'nlab bo'sh papkalar to'planadi.

Yechim: fon monitor har `SCAN_INTERVAL` soniyada PROJECTS_BASE_DIR'ni tekshiradi.
Papka `MIN_AGE_SECONDS` dan katta bo'lsa VA "bo'sh" mezoniga to'g'ri kelsa —
o'chiriladi. Har tozalash `janitor_log.jsonl` ga yoziladi.

"Bo'sh" mezonlari:
  * Papkada foydali fayllar yo'q (yashirin va vaqtinchalik fayllar hisobga olinmaydi).
  * Yoki papkada faqat bir necha kilobayt hajmdagi placeholder fayllar bor.
  * `.git`, `.env` va boshqa muhim marker fayllar mavjud bo'lsa — hech qachon o'chirilmaydi.
"""
import time
import json
import shutil
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional


# Muhim fayllar — mavjud bo'lsa papka o'chirilmaydi (foydalanuvchi ish qilgan).
PROTECTED_FILENAMES = {
    ".git", ".gitignore", ".env", ".env.local", ".env.example",
    "README.md", "readme.md", "package.json", "pyproject.toml", "requirements.txt",
    "Cargo.toml", "go.mod", "composer.json", "Gemfile", "Dockerfile",
    "index.html", "main.py", "app.py", "server.py", "main.go", "main.rs",
    "src", "app", "public", "static",
}

# Ignore qilingan (mavjud bo'lsa ham "foydali" sanaladi lekin hisoblanmaydi).
IGNORED_FILENAMES = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".cache",
}


class WorkspaceJanitor:
    """PROJECTS_BASE_DIR ichidagi bo'sh loyiha papkalarini kuzatib boradi."""

    SCAN_INTERVAL_SECONDS = 45.0
    MIN_AGE_SECONDS = 90.0             # yaratilganidan keyin kamida shuncha vaqt kutish
    MAX_USEFUL_BYTES = 128             # bundan kichik "chiqindi" fayllar bo'sh sanaladi
    ENABLED = True
    LOG_TAIL = 50                      # snapshot uchun oxirgi shuncha yozuv saqlanadi

    def __init__(self, projects_base_dir_getter, log_path: Path,
                 is_orchestration_active_getter=None):
        """
        projects_base_dir_getter — callable, joriy loyihalar katalogini qaytaradi
                                    (Path). Katalog jonli o'zgarganda ham to'g'ri
                                    yangi manzil qaytishi shart.
        is_orchestration_active_getter — callable, hozirda orkestratsiya
                                    ishlayotganini bildiradi (True bo'lsa skipni afzal ko'ramiz).
        """
        self._get_dir = projects_base_dir_getter
        self._is_busy = is_orchestration_active_getter or (lambda: False)
        self.log_path = Path(log_path)
        self.task: Optional[asyncio.Task] = None
        self.stats = {
            "scans": 0,
            "removed_total": 0,
            "last_scan_ts": 0.0,
            "last_removed": [],   # eng oxirgi tozalashda o'chirilgan papkalar
            "next_scan_in": 0.0,
        }
        # Yaqinda ko'rilgan papkalar — birinchi ko'rish vaqtini eslab qolamiz.
        # Papka MIN_AGE dan katta bo'lgandagina o'chirish mumkin.
        self._first_seen: Dict[str, float] = {}

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Fon vazifasini ishga tushiradi."""
        if self.task and not self.task.done():
            return
        loop = loop or asyncio.get_event_loop()
        self.task = loop.create_task(self._run_forever())

    def stop(self):
        if self.task and not self.task.done():
            self.task.cancel()

    async def _run_forever(self):
        while True:
            try:
                if self.ENABLED and not self._is_busy():
                    await asyncio.to_thread(self._scan_once)
                self.stats["next_scan_in"] = self.SCAN_INTERVAL_SECONDS
                await asyncio.sleep(self.SCAN_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                return
            except Exception as e:
                self._log_error(str(e))
                await asyncio.sleep(30.0)

    def _is_project_empty(self, project_dir: Path) -> Dict[str, Any]:
        """
        Papka "bo'sh"mi (foydali fayl yo'qmi)ni aniqlaydi.
        Qaytaradi: {"empty": bool, "reason": str, "useful_files": int, "size_bytes": int}
        """
        try:
            entries = list(project_dir.iterdir())
        except (PermissionError, OSError) as e:
            return {"empty": False, "reason": f"kirish yo'q: {e}", "useful_files": 0, "size_bytes": 0}

        # Himoyalangan marker bor bo'lsa — hech qachon o'chirmaymiz.
        for e in entries:
            if e.name in PROTECTED_FILENAMES:
                return {"empty": False, "reason": f"himoyalangan: {e.name}",
                        "useful_files": 1, "size_bytes": 0}

        useful = 0
        total_bytes = 0
        for e in entries:
            if e.name in IGNORED_FILENAMES or e.name.startswith("."):
                continue
            if e.is_file():
                try:
                    sz = e.stat().st_size
                except Exception:
                    sz = 0
                if sz > self.MAX_USEFUL_BYTES:
                    useful += 1
                    total_bytes += sz
            elif e.is_dir():
                # Ichki papkada foydali fayllar bormi? Bir marta chuqurroq qaraymiz.
                try:
                    sub = list(e.rglob("*"))
                except Exception:
                    sub = []
                for s in sub:
                    if s.is_file() and s.name not in IGNORED_FILENAMES and not s.name.startswith("."):
                        try:
                            sz = s.stat().st_size
                        except Exception:
                            sz = 0
                        if sz > self.MAX_USEFUL_BYTES:
                            useful += 1
                            total_bytes += sz

        if useful == 0:
            return {"empty": True, "reason": "foydali fayl yo'q",
                    "useful_files": 0, "size_bytes": total_bytes}
        return {"empty": False, "reason": f"{useful} ta fayl mavjud",
                "useful_files": useful, "size_bytes": total_bytes}

    def _scan_once(self):
        """Bir marta skan qiladi va munosib papkalarni o'chiradi."""
        base = self._get_dir()
        if not base or not Path(base).exists() or not Path(base).is_dir():
            return
        base = Path(base)
        now = time.time()
        removed_this_round: List[Dict[str, Any]] = []

        try:
            children = [p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")]
        except (PermissionError, OSError):
            return

        active_names = set()
        for p in children:
            key = str(p.resolve())
            active_names.add(key)
            if key not in self._first_seen:
                self._first_seen[key] = now

            age = now - self._first_seen[key]
            if age < self.MIN_AGE_SECONDS:
                continue

            check = self._is_project_empty(p)
            if not check["empty"]:
                continue

            # Xavfsizlik chegarasi: base dan tashqariga chiqmagan bo'lsin.
            try:
                p.resolve().relative_to(base.resolve())
            except ValueError:
                continue

            try:
                shutil.rmtree(p)
                removed_this_round.append({
                    "path": str(p), "name": p.name,
                    "age_seconds": round(age, 1),
                    "reason": check["reason"],
                })
                self._first_seen.pop(key, None)
            except Exception as e:
                self._log_error(f"remove failed {p}: {e}")

        # Kuzatuvdan chiqarilgan papkalarni ham o'chiramiz (endi mavjud emas)
        stale_keys = [k for k in self._first_seen if k not in active_names]
        for k in stale_keys:
            self._first_seen.pop(k, None)

        self.stats["scans"] += 1
        self.stats["last_scan_ts"] = now
        self.stats["last_removed"] = removed_this_round
        self.stats["removed_total"] += len(removed_this_round)

        if removed_this_round:
            self._append_log({
                "ts": now,
                "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "removed": removed_this_round,
                "base": str(base),
            })

    def _append_log(self, entry: Dict[str, Any]):
        try:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _log_error(self, msg: str):
        self._append_log({"ts": time.time(),
                          "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "error": msg})

    def read_recent_log(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Log faylining oxirgi qatorlarini o'qiydi."""
        if not self.log_path.exists():
            return []
        try:
            lines = self.log_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        out = []
        for ln in lines[-limit:]:
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return out

    def snapshot(self) -> Dict[str, Any]:
        """UI uchun holat rasmi."""
        return {
            "enabled": self.ENABLED,
            "scans_total": self.stats["scans"],
            "removed_total": self.stats["removed_total"],
            "last_scan_ts": self.stats["last_scan_ts"],
            "last_scan_iso": (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.stats["last_scan_ts"]))
                              if self.stats["last_scan_ts"] else None),
            "last_removed": self.stats["last_removed"][-10:],
            "watched_folders": len(self._first_seen),
            "scan_interval_s": self.SCAN_INTERVAL_SECONDS,
            "min_age_s": self.MIN_AGE_SECONDS,
        }

    def force_scan(self) -> Dict[str, Any]:
        """UI orqali qo'lda tozalash — MIN_AGE ni chetlab o'tmaydi."""
        self._scan_once()
        return self.snapshot()
