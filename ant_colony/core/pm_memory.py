"""
PM Memory — Project Manager'ning uzoq muddatli xotirasi.

Har bir tugagan orkestratsiyadan kompakt xulosa saqlanadi. PM yangi topshiriq
tahlil qilayotganda va bo'sh qolganda shu xotiraga murojaat qiladi:

    * `completed_projects`: yaqin tugagan loyihalar (task, files, score, ts)
    * `future_plans`: foydalanuvchi "keyinroq X qilamiz" degan narsalar
    * `open_questions`: PM CEO ga bermoqchi bo'lgan savollar
    * `preferences`: foydalanuvchi ustuvorliklari (masalan "Python backend afzal")

Xotira JSON fayl sifatida ishchi papkada saqlanadi — restart'da ham eslab qoladi.
"""
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


# JSON'ni bir vaqtning o'zida ikki joydan yozib buzmaslik uchun.
_LOCK = threading.Lock()

# Max entries — cheksiz o'sib ketmasin (LLM konteksti chegarasi bor).
MAX_COMPLETED_PROJECTS = 30
MAX_FUTURE_PLANS = 20
MAX_OPEN_QUESTIONS = 10

# Default bo'sh struktura
_DEFAULT: Dict[str, Any] = {
    "version": 1,
    "created_at": None,
    "updated_at": None,
    "completed_projects": [],  # {task, project_dir, files, score, duration_s, ts, iso}
    "future_plans": [],        # {text, added_ts, iso, source}
    "open_questions": [],      # {question, ts, iso}
    "preferences": {},         # {key: value}
    "stats": {
        "total_orchestrations": 0,
        "total_files_produced": 0,
        "avg_score": 0.0,
    },
}


class PMMemory:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._cache: Optional[Dict[str, Any]] = None

    def _load(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "completed_projects" in data:
                    self._cache = data
                    return data
            except Exception:
                pass
        # Bo'sh xotira yaratamiz
        d = json.loads(json.dumps(_DEFAULT))  # deep copy
        d["created_at"] = time.time()
        d["updated_at"] = time.time()
        self._cache = d
        self._save(d)
        return d

    def _save(self, data: Dict[str, Any]):
        data["updated_at"] = time.time()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp fayl orqali
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        with _LOCK:
            return json.loads(json.dumps(self._load()))  # nusxa

    def record_orchestration(
        self,
        task: str,
        project_dir: Optional[str],
        files: List[str],
        score: Optional[float],
        duration_s: float,
        summary: Optional[str] = None,
    ):
        """Tugagan orkestratsiya haqida xotiraga yozadi."""
        with _LOCK:
            data = self._load()
            entry = {
                "task": (task or "")[:400],
                "project_dir": project_dir,
                "files": (files or [])[:20],
                "files_count": len(files or []),
                "score": round(score, 1) if isinstance(score, (int, float)) else None,
                "duration_s": round(float(duration_s or 0), 1),
                "summary": (summary or "")[:400] if summary else None,
                "ts": time.time(),
                "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            data["completed_projects"].insert(0, entry)
            data["completed_projects"] = data["completed_projects"][:MAX_COMPLETED_PROJECTS]

            # Statistikani yangilash
            s = data["stats"]
            s["total_orchestrations"] = int(s.get("total_orchestrations", 0)) + 1
            s["total_files_produced"] = int(s.get("total_files_produced", 0)) + len(files or [])
            # Ballar bo'yicha yig'ma o'rtacha
            scored = [c["score"] for c in data["completed_projects"] if isinstance(c.get("score"), (int, float))]
            s["avg_score"] = round(sum(scored) / len(scored), 1) if scored else 0.0

            self._save(data)

    def add_future_plan(self, text: str, source: str = "user"):
        text = (text or "").strip()
        if not text:
            return
        with _LOCK:
            data = self._load()
            # Duplikat tekshiruvi (birinchi 80 belgi mos kelsa)
            key = text[:80].lower()
            for p in data["future_plans"]:
                if p.get("text", "")[:80].lower() == key:
                    return
            data["future_plans"].insert(0, {
                "text": text[:400],
                "added_ts": time.time(),
                "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source": source,
            })
            data["future_plans"] = data["future_plans"][:MAX_FUTURE_PLANS]
            self._save(data)

    def remove_future_plan(self, index: int):
        with _LOCK:
            data = self._load()
            if 0 <= index < len(data["future_plans"]):
                data["future_plans"].pop(index)
                self._save(data)

    def add_open_question(self, question: str):
        q = (question or "").strip()
        if not q:
            return
        with _LOCK:
            data = self._load()
            data["open_questions"].insert(0, {
                "question": q[:400],
                "ts": time.time(),
                "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            data["open_questions"] = data["open_questions"][:MAX_OPEN_QUESTIONS]
            self._save(data)

    def set_preference(self, key: str, value: Any):
        with _LOCK:
            data = self._load()
            data["preferences"][str(key)[:64]] = value
            self._save(data)

    def clear(self, keep_preferences: bool = True):
        """Xotirani tozalaydi — masalan foydalanuvchi so'ragan bo'lsa."""
        with _LOCK:
            prefs = self._load().get("preferences", {}) if keep_preferences else {}
            d = json.loads(json.dumps(_DEFAULT))
            d["created_at"] = time.time()
            d["updated_at"] = time.time()
            d["preferences"] = prefs
            self._cache = d
            self._save(d)

    # --- PM prompt uchun yordamchi: xotirani kompakt matnga aylantiradi ---

    def as_context_snippet(self, max_projects: int = 5) -> str:
        """PM system prompt'ga qo'shiladigan qisqa xotira xulasi."""
        d = self.snapshot()
        parts: List[str] = []

        completed = d.get("completed_projects", [])[:max_projects]
        if completed:
            parts.append("### So'nggi tugagan loyihalar (kontekst uchun):")
            for c in completed:
                score = f", ball: {c['score']}" if c.get("score") is not None else ""
                fc = c.get("files_count", 0)
                parts.append(f"- **{c.get('iso', '?')}** ({c.get('duration_s', 0)}s, {fc} fayl{score}): {c.get('task', '')[:150]}")

        plans = d.get("future_plans", [])
        if plans:
            parts.append("\n### Kelajakdagi rejalar (foydalanuvchi eslab qolishimni so'ragan):")
            for i, p in enumerate(plans):
                parts.append(f"- [{i}] {p.get('text', '')[:200]}")

        prefs = d.get("preferences", {})
        if prefs:
            parts.append("\n### Foydalanuvchi ustuvorliklari:")
            for k, v in prefs.items():
                parts.append(f"- {k}: {v}")

        return "\n".join(parts).strip()

    # Idle chaqiruv uchun dinamik hint
    def build_idle_greeting(self) -> Dict[str, Any]:
        """PM idle bo'lganda foydalanuvchiga aytadigan dinamik xabar."""
        d = self.snapshot()
        completed = d.get("completed_projects", [])
        plans = d.get("future_plans", [])
        stats = d.get("stats", {})

        return {
            "total_orchestrations": stats.get("total_orchestrations", 0),
            "avg_score": stats.get("avg_score", 0),
            "last_project": (completed[0] if completed else None),
            "pending_plans": plans[:3],
            "pending_plans_total": len(plans),
        }


# Global singleton (server startup'da inisializatsiya qilinadi)
_MEMORY: Optional[PMMemory] = None


def init_memory(path: Path) -> PMMemory:
    global _MEMORY
    _MEMORY = PMMemory(path)
    return _MEMORY


def get_memory() -> Optional[PMMemory]:
    return _MEMORY
