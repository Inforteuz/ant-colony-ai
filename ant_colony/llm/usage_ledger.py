"""
Token Usage Ledger — har bir LLM chaqirig'ini kim, qaysi provayder, qaysi model
va qaysi vazifa uchun sarflaganini yozib boruvchi hisob daftari.

NIMA UCHUN KERAK
----------------
Ilgari platformada faqat umumiy `total_prompt_tokens` / `total_completion_tokens`
hisoblanardi va u ham `record_usage()` ga `model_id` uzatilmagani uchun model
kesimida hech qachon to'lmasdi. Natijada eng muhim savollarga javob yo'q edi:

    * qaysi provayderga qancha token ketdi?
    * qaysi model qanchasini yedi?
    * BITTA vazifa (topshiriq) qancha tokenga tushdi?
    * qaysi agent (PM / coder / QA / security) eng qimmatga tushyapti?

Bu modul aynan shu uchta kesimni (provayder, model, vazifa) va qo'shimcha
agent kesimini beradi.

ARXITEKTURA
-----------
    contextvars  — joriy vazifa va joriy agent "scope"i. LLM chaqirig'i qayerda
                   bo'lmasin, o'zi qaysi vazifaga tegishli ekanini biladi.
    record()     — bitta chaqiruv fakti (append-only jurnal + agregatlar).
    persist      — data/usage/ ichida JSONL jurnal + JSON agregatlar.

Jurnal disk uchun cheklangan (rotatsiya bilan), lekin agregatlar hech qachon
yo'qolmaydi — ular alohida faylda umr bo'yi yig'iladi.
"""
import csv
import io
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from ant_colony.config import DATA_DIR, MODELS_CATALOG, PROVIDERS

USAGE_DIR: Path = DATA_DIR / "usage"
CALLS_FILE: Path = USAGE_DIR / "calls.jsonl"
CALLS_ARCHIVE: Path = USAGE_DIR / "calls.1.jsonl"
TASKS_FILE: Path = USAGE_DIR / "tasks.json"
TOTALS_FILE: Path = USAGE_DIR / "totals.json"
PRICING_FILE: Path = DATA_DIR / "model_pricing.json"

# Jurnal shu qatordan oshsa arxivga ko'chiriladi (disk cheksiz o'smasin).
MAX_CALL_LINES = 20000
# Xotirada saqlanadigan oxirgi chaqiruvlar (UI "so'nggi chaqiruvlar" uchun).
MAX_MEMORY_CALLS = 2000
# Saqlanadigan vazifalar soni.
MAX_TASKS = 300
# Agregatlarni diskka yozish chastotasi.
FLUSH_EVERY_CALLS = 5
FLUSH_EVERY_SECONDS = 10.0


# --- Joriy kontekst (vazifa / agent) ---------------------------------------

_task_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("ant_usage_task", default=None)
_agent_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("ant_usage_agent", default=None)


def _safe_reset(var: ContextVar, token: Any) -> None:
    """
    Kontekstni tiklaydi.

    Async generator boshqa task ichida yopilishi mumkin — bunday holatda
    `reset()` ValueError beradi. Bu telemetriya, shu sababli u hech qachon
    asosiy oqimni buzmasligi kerak.
    """
    try:
        var.reset(token)
    except ValueError:
        var.set(None)


def _provider_label(provider_id: str) -> str:
    prov = PROVIDERS.get(provider_id) or {}
    return prov.get("name") or provider_id or "—"


def _model_meta(model_id: str) -> Dict[str, Any]:
    return next((m for m in MODELS_CATALOG if m["id"] == model_id), {})


def _empty_bucket() -> Dict[str, Any]:
    return {
        "calls": 0,
        "cached_calls": 0,
        "failed_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "tokens_saved": 0,
        "duration_ms": 0,
        "cost_usd": 0.0,
        "cost_known_calls": 0,
        "first_seen": None,
        "last_seen": None,
    }


def _without_cost(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent qatorlaridan narx maydonlarini olib tashlaydi.

    Bitta agent bir nechta modelni ishlatishi mumkin, shuning uchun uni model
    kesimisiz narxlash noto'g'ri raqam berardi — yo'q raqamni ko'rsatgandan
    ko'ra umuman ko'rsatmagan ma'qul.
    """
    return {k: v for k, v in row.items()
            if k not in ("cost_usd", "cost_known", "cost_known_calls", "cost_partial")}


def _add(bucket: Dict[str, Any], rec: Dict[str, Any]) -> None:
    bucket["calls"] += 1
    if rec.get("cached"):
        bucket["cached_calls"] += 1
    if not rec.get("success", True):
        bucket["failed_calls"] += 1
    for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
        bucket[key] += int(rec.get(key) or 0)
    bucket["tokens_saved"] += int(rec.get("tokens_saved") or 0)
    bucket["duration_ms"] += int(rec.get("duration_ms") or 0)
    cost = rec.get("cost_usd")
    if cost is not None:
        bucket["cost_usd"] = round(bucket["cost_usd"] + float(cost), 6)
        bucket["cost_known_calls"] += 1
    ts = rec.get("ts") or time.time()
    if bucket["first_seen"] is None:
        bucket["first_seen"] = ts
    bucket["last_seen"] = ts


class UsageLedger:
    """Thread-safe token hisob daftari (bitta jarayon ichida yagona nusxa)."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # Saqlash yo'llari nusxaga bog'liq: testlar vaqtinchalik papkada ishlaydi
        # va foydalanuvchining haqiqiy hisobotini hech qachon o'chirmaydi.
        self.base_dir: Path = Path(base_dir) if base_dir else USAGE_DIR
        self.calls_file: Path = self.base_dir / "calls.jsonl"
        self.calls_archive: Path = self.base_dir / "calls.1.jsonl"
        self.tasks_file: Path = self.base_dir / "tasks.json"
        self.totals_file: Path = self.base_dir / "totals.json"

        self._lock = threading.RLock()
        self._dirty = 0
        self._last_flush = 0.0
        self._pricing: Dict[str, Any] = {}
        self._pricing_mtime: float = -1.0

        self.by_provider: Dict[str, Dict[str, Any]] = {}
        self.by_model: Dict[str, Dict[str, Any]] = {}
        self.by_provider_model: Dict[str, Dict[str, Any]] = {}
        self.by_agent: Dict[str, Dict[str, Any]] = {}
        self.totals: Dict[str, Any] = _empty_bucket()
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.recent_calls: List[Dict[str, Any]] = []
        self.started_at: float = time.time()

        self._load()

    # --- Saqlash ----------------------------------------------------------

    def _load(self) -> None:
        try:
            if self.totals_file.exists():
                data = json.loads(self.totals_file.read_text(encoding="utf-8"))
                self.by_provider = data.get("by_provider") or {}
                self.by_model = data.get("by_model") or {}
                self.by_provider_model = data.get("by_provider_model") or {}
                self.by_agent = data.get("by_agent") or {}
                self.totals = {**_empty_bucket(), **(data.get("totals") or {})}
                self.started_at = data.get("started_at") or self.started_at
        except Exception:
            # Buzuq fayl butun platformani to'xtatmasin — noldan boshlaymiz.
            pass

        try:
            if self.tasks_file.exists():
                raw = json.loads(self.tasks_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self.tasks = raw.get("tasks") or {}
        except Exception:
            self.tasks = {}

    def _flush(self, force: bool = False) -> None:
        """Agregatlarni diskka yozadi (har chaqiruvda emas — throttling bilan)."""
        now = time.time()
        if not force and self._dirty < FLUSH_EVERY_CALLS and (now - self._last_flush) < FLUSH_EVERY_SECONDS:
            return
        self.base_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "started_at": self.started_at,
            "updated_at": now,
            "totals": self.totals,
            "by_provider": self.by_provider,
            "by_model": self.by_model,
            "by_provider_model": self.by_provider_model,
            "by_agent": self.by_agent,
        }
        self._atomic_write(self.totals_file, payload)

        trimmed = sorted(self.tasks.values(), key=lambda t: t.get("started_at") or 0)[-MAX_TASKS:]
        self.tasks = {t["task_id"]: t for t in trimmed}
        self._atomic_write(self.tasks_file, {"version": 1, "tasks": self.tasks})

        self._dirty = 0
        self._last_flush = now

    @staticmethod
    def _atomic_write(path: Path, payload: Any) -> None:
        try:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
            os.chmod(path, 0o600)
        except Exception:
            pass

    def _append_jsonl(self, rec: Dict[str, Any]) -> None:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            if self.calls_file.exists() and self._line_estimate() > MAX_CALL_LINES:
                self.calls_file.replace(self.calls_archive)
            with self.calls_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

    _line_count_cache: int = 0

    def _line_estimate(self) -> int:
        # Har yozuvda faylni sanash qimmat — hisobni xotirada olib boramiz va
        # faqat dastur qayta ishga tushganda bir marta aniqlaymiz.
        if self._line_count_cache <= 0:
            try:
                with self.calls_file.open("rb") as fh:
                    self._line_count_cache = sum(1 for _ in fh)
            except Exception:
                self._line_count_cache = 0
        self._line_count_cache += 1
        if self._line_count_cache > MAX_CALL_LINES:
            self._line_count_cache = 0
        return self._line_count_cache

    # --- Narxlash ---------------------------------------------------------

    def _load_pricing(self) -> Dict[str, Any]:
        """
        Narx jadvali FOYDALANUVCHI fayli — biz narxlarni o'ylab topmaymiz.

        data/model_pricing.json:
            {"models": {"gpt-4o": {"input_per_1m": 2.5, "output_per_1m": 10}},
             "providers": {"groq": {"input_per_1m": 0, "output_per_1m": 0}}}

        Fayl bo'lmasa — narx "noma'lum" (null) bo'lib qoladi va UI uni
        ko'rsatmaydi. Katalogda `is_free: true` bo'lgan modellar 0 deb olinadi.
        """
        try:
            mtime = PRICING_FILE.stat().st_mtime if PRICING_FILE.exists() else -1.0
        except OSError:
            mtime = -1.0
        if mtime != self._pricing_mtime:
            self._pricing_mtime = mtime
            try:
                self._pricing = json.loads(PRICING_FILE.read_text(encoding="utf-8")) if mtime > 0 else {}
            except Exception:
                self._pricing = {}
        return self._pricing

    def estimate_cost(self, model_id: str, provider_id: str,
                      prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        pricing = self._load_pricing()
        rate = (pricing.get("models") or {}).get(model_id)
        if rate is None:
            rate = (pricing.get("providers") or {}).get(provider_id)
        if rate is None:
            # Katalogda bepul deb belgilangan model — 0. Aks holda noma'lum.
            if _model_meta(model_id).get("is_free"):
                return 0.0
            return None
        try:
            inp = float(rate.get("input_per_1m", 0) or 0)
            out = float(rate.get("output_per_1m", 0) or 0)
        except (TypeError, ValueError):
            return None
        return round((prompt_tokens / 1_000_000) * inp + (completion_tokens / 1_000_000) * out, 6)

    # --- Kontekst scope'lari ---------------------------------------------

    @contextmanager
    def task_scope(self, task_id: str, label: str = "", kind: str = "orchestration") -> Iterator[Dict[str, Any]]:
        """Vazifa doirasi — ichidagi HAR QANDAY LLM chaqirig'i shu vazifaga yoziladi."""
        task = self.begin_task(task_id, label, kind)
        token = _task_ctx.set({"task_id": task_id, "label": label, "kind": kind})
        try:
            yield task
        finally:
            _safe_reset(_task_ctx, token)
            # Fon xizmatlari (tavsiyalar, 3D dialoglar) bir xil id bilan qayta-qayta
            # ishlaydi. Ular chiqishda yopiladi, aks holda ro'yxatda abadiy
            # "выполняется" bo'lib osilib qolardi.
            if kind == "system":
                self.finish_task(task_id, status="completed")

    @contextmanager
    def agent_scope(self, agent: str, role: str = "", phase: str = "") -> Iterator[None]:
        """Agent doirasi — chaqiruvlar qaysi agentga tegishli ekanini belgilaydi."""
        token = _agent_ctx.set({"agent": agent or "—", "role": role or "", "phase": phase or ""})
        try:
            yield
        finally:
            _safe_reset(_agent_ctx, token)

    @staticmethod
    def current_task_id() -> Optional[str]:
        ctx = _task_ctx.get()
        return ctx.get("task_id") if ctx else None

    # --- Vazifa hayot sikli ----------------------------------------------

    def begin_task(self, task_id: str, label: str = "", kind: str = "orchestration") -> Dict[str, Any]:
        with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                task = {
                    "task_id": task_id,
                    "label": (label or "").strip()[:400],
                    "kind": kind,
                    "status": "running",
                    "started_at": time.time(),
                    "finished_at": None,
                    "duration_s": None,
                    "score": None,
                    "project_dir": None,
                    "totals": _empty_bucket(),
                    "by_provider": {},
                    "by_model": {},
                    "by_agent": {},
                    "calls": [],
                }
                self.tasks[task_id] = task
            elif kind == "system":
                # Takrorlanuvchi tizim vazifasi — har chaqiruvda yangi sikl boshlanadi,
                # shu sababli davomiylik birinchi ishga tushishdan emas, oxirgisidan
                # hisoblanadi.
                task["started_at"] = time.time()
                task["status"] = "running"
            self._dirty += 1
            self._flush()
            return task

    def finish_task(self, task_id: str, *, status: str = "completed",
                    score: Optional[float] = None, project_dir: Optional[str] = None) -> None:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            task["status"] = status
            task["finished_at"] = time.time()
            task["duration_s"] = round(task["finished_at"] - (task.get("started_at") or task["finished_at"]), 2)
            if score is not None:
                task["score"] = score
            if project_dir:
                task["project_dir"] = project_dir
            self._flush(force=True)

    # --- Asosiy yozuv -----------------------------------------------------

    def record(
        self,
        *,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        reasoning_tokens: int = 0,
        total_tokens: Optional[int] = None,
        tokens_saved: int = 0,
        duration_ms: int = 0,
        cached: bool = False,
        success: bool = True,
        requested_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bitta LLM chaqiruvini yozadi va joriy vazifa/agent kesimlariga qo'shadi.

        `total_tokens` provayder bergan bo'lsa o'sha ishlatiladi (ba'zi
        provayderlar prompt+completion yig'indisidan farq qiladigan qiymat
        beradi), aks holda o'zimiz yig'amiz.
        """
        prompt_tokens = int(prompt_tokens or 0)
        completion_tokens = int(completion_tokens or 0)
        reasoning_tokens = int(reasoning_tokens or 0)
        if total_tokens is None or int(total_tokens or 0) <= 0:
            total_tokens = prompt_tokens + completion_tokens
        total_tokens = int(total_tokens)

        provider = provider or "unknown"
        model = model or "unknown"

        task_ctx = _task_ctx.get() or {}
        agent_ctx = _agent_ctx.get() or {}

        rec: Dict[str, Any] = {
            "ts": time.time(),
            "provider": provider,
            "provider_label": _provider_label(provider),
            "model": model,
            "requested_model": requested_model or model,
            "fallback": bool(requested_model and requested_model != model),
            "task_id": task_ctx.get("task_id"),
            "task_label": task_ctx.get("label", ""),
            "task_kind": task_ctx.get("kind", ""),
            "agent": agent_ctx.get("agent", "system"),
            "role": agent_ctx.get("role", ""),
            "phase": agent_ctx.get("phase", ""),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "tokens_saved": int(tokens_saved or 0),
            "duration_ms": int(duration_ms or 0),
            "cached": bool(cached),
            "success": bool(success),
        }
        rec["cost_usd"] = self.estimate_cost(model, provider, prompt_tokens, completion_tokens)

        with self._lock:
            _add(self.totals, rec)
            _add(self.by_provider.setdefault(provider, _empty_bucket()), rec)
            _add(self.by_model.setdefault(model, _empty_bucket()), rec)
            _add(self._dims(self.by_provider_model, f"{provider}::{model}", provider, model), rec)
            _add(self.by_agent.setdefault(rec["agent"], _empty_bucket()), rec)

            task_id = rec["task_id"]
            if task_id:
                task = self.tasks.get(task_id) or self.begin_task(task_id, rec["task_label"], rec["task_kind"] or "orchestration")
                _add(task["totals"], rec)
                _add(task["by_provider"].setdefault(provider, _empty_bucket()), rec)
                _add(self._dims(task["by_model"], model, provider, model), rec)
                _add(task["by_agent"].setdefault(rec["agent"], _empty_bucket()), rec)
                # Vazifa ichidagi chaqiruvlar ro'yxati — "qaysi qadam qancha yedi".
                task["calls"].append({
                    k: rec[k] for k in (
                        "ts", "provider", "model", "agent", "role", "phase",
                        "prompt_tokens", "completion_tokens", "reasoning_tokens",
                        "total_tokens", "tokens_saved", "duration_ms", "cached",
                        "success", "fallback", "cost_usd",
                    )
                })
                if len(task["calls"]) > 500:
                    del task["calls"][:-500]

            self.recent_calls.append(rec)
            if len(self.recent_calls) > MAX_MEMORY_CALLS:
                del self.recent_calls[:-MAX_MEMORY_CALLS]

            self._dirty += 1
            self._append_jsonl(rec)
            self._flush()

        return rec

    # --- O'qish / hisobotlar ---------------------------------------------

    @staticmethod
    def _dims(store: Dict[str, Dict[str, Any]], key: str, provider: str, model: str) -> Dict[str, Any]:
        """
        Model darajasidagi bucket — o'z provayderi va modelini eslab qoladi.

        Bu narxni O'QISH paytida qayta hisoblash uchun kerak: foydalanuvchi
        prays-listni keyinroq qo'shsa, butun tarix darhol qayta narxlanadi.
        """
        bucket = store.setdefault(key, _empty_bucket())
        bucket["provider"] = provider
        bucket["model"] = model
        return bucket

    def _bucket_cost(self, bucket: Dict[str, Any]) -> Optional[float]:
        """Bitta model bucket'ining joriy prays bo'yicha narxi."""
        return self.estimate_cost(
            bucket.get("model", ""), bucket.get("provider", ""),
            bucket.get("prompt_tokens", 0), bucket.get("completion_tokens", 0),
        )

    def _cost_over(self, buckets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bir nechta model bucket'i bo'yicha jamlangan narx.

        Narxi noma'lum model bo'lsa — u jamiga qo'shilmaydi, lekin `partial`
        bayrog'i ko'tariladi. Shunda UI "to'liq emas"ligini ochiq aytadi va
        biz hech qanday raqamni O'YLAB TOPMAYMIZ.
        """
        total = 0.0
        known = 0
        unknown = 0
        for b in buckets:
            if not b.get("total_tokens") and not b.get("calls"):
                continue
            cost = self._bucket_cost(b)
            if cost is None:
                unknown += 1
            else:
                total += cost
                known += 1
        return {
            "cost_usd": round(total, 6) if known else 0.0,
            "cost_known": known > 0,
            "cost_partial": bool(known and unknown),
        }

    @staticmethod
    def _view(key: str, bucket: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
        calls = bucket.get("calls", 0) or 0
        total = bucket.get("total_tokens", 0) or 0
        out = {
            "key": key,
            **{k: v for k, v in bucket.items()},
            "avg_tokens_per_call": round(total / calls) if calls else 0,
            "avg_latency_ms": round((bucket.get("duration_ms", 0) or 0) / calls) if calls else 0,
            # Narx faqat kamida bitta chaqiruvda ma'lum bo'lsa ko'rsatiladi.
            "cost_known": bool(bucket.get("cost_known_calls")),
        }
        out.update(extra)
        return out

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            grand = self.totals.get("total_tokens", 0) or 0

            all_model_buckets = list(self.by_provider_model.values())

            providers = []
            for pid, bucket in self.by_provider.items():
                children = [b for b in all_model_buckets if b.get("provider") == pid]
                providers.append(self._view(
                    pid, bucket,
                    provider=pid,
                    provider_label=_provider_label(pid),
                    share_pct=round((bucket.get("total_tokens", 0) / grand) * 100, 1) if grand else 0.0,
                    **self._cost_over(children),
                ))
            providers.sort(key=lambda p: p["total_tokens"], reverse=True)

            models = []
            for combo, bucket in self.by_provider_model.items():
                pid, _, mid = combo.partition("::")
                meta = _model_meta(mid)
                models.append(self._view(
                    combo, bucket,
                    provider=pid,
                    provider_label=_provider_label(pid),
                    model=mid,
                    model_name=meta.get("name") or mid,
                    is_free=bool(meta.get("is_free")),
                    share_pct=round((bucket.get("total_tokens", 0) / grand) * 100, 1) if grand else 0.0,
                    **self._cost_over([bucket]),
                ))
            models.sort(key=lambda m: m["total_tokens"], reverse=True)

            # Agent kesimida narx ko'rsatilmaydi: bitta agent bir nechta modelni
            # ishlatgan bo'lishi mumkin va uni model bo'yicha ajratmasdan
            # narxlash noto'g'ri raqam berardi. Bu yerda faqat tokenlar.
            agents = [_without_cost(self._view(a, b, agent=a)) for a, b in self.by_agent.items()]
            agents.sort(key=lambda a: a["total_tokens"], reverse=True)

            tasks = self._task_rows()
            # O'rtacha "bitta vazifaga" ko'rsatkichi FAQAT foydalanuvchi
            # topshiriqlaridan hisoblanadi: fon xizmatlari (tavsiyalar, 3D
            # dialoglar) uni sun'iy ravishda pasaytirib yuborardi.
            finished = [t for t in tasks
                        if t["kind"] != "system" and t["status"] != "running" and t["total_tokens"] > 0]
            avg_task_tokens = round(sum(t["total_tokens"] for t in finished) / len(finished)) if finished else 0

            return {
                "totals": {
                    **self.totals,
                    "avg_tokens_per_call": round(grand / self.totals["calls"]) if self.totals["calls"] else 0,
                    "avg_tokens_per_task": avg_task_tokens,
                    "tasks_counted": len(finished),
                    **self._cost_over(all_model_buckets),
                },
                "by_provider": providers,
                "by_model": models,
                "by_agent": agents,
                "tasks": tasks[:50],
                "pricing_configured": bool(self._load_pricing()),
                "pricing_file": str(PRICING_FILE),
                "started_at": self.started_at,
                "generated_at": time.time(),
            }

    def _task_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for task in self.tasks.values():
            totals = task.get("totals") or _empty_bucket()
            # Hali birorta chaqiruv bo'lmagan vazifa ro'yxatda ko'rinmaydi —
            # aks holda "0 token" qatorlari hisobotni ifloslantirardi.
            if not totals.get("calls"):
                continue
            cost = self._cost_over(list((task.get("by_model") or {}).values()))
            rows.append({
                "task_id": task["task_id"],
                "label": task.get("label", ""),
                "kind": task.get("kind", ""),
                "status": task.get("status", ""),
                "started_at": task.get("started_at"),
                "finished_at": task.get("finished_at"),
                "duration_s": task.get("duration_s"),
                "score": task.get("score"),
                "project_dir": task.get("project_dir"),
                "calls": totals.get("calls", 0),
                "prompt_tokens": totals.get("prompt_tokens", 0),
                "completion_tokens": totals.get("completion_tokens", 0),
                "reasoning_tokens": totals.get("reasoning_tokens", 0),
                "total_tokens": totals.get("total_tokens", 0),
                "tokens_saved": totals.get("tokens_saved", 0),
                **cost,
                "models_used": len(task.get("by_model") or {}),
                "providers_used": len(task.get("by_provider") or {}),
            })
        rows.sort(key=lambda t: t.get("started_at") or 0, reverse=True)
        return rows

    def task_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return self._task_rows()[:max(1, min(int(limit or 100), MAX_TASKS))]

    def task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            totals = task.get("totals") or _empty_bucket()
            grand = totals.get("total_tokens", 0) or 0

            model_buckets = list((task.get("by_model") or {}).values())

            def rows(bucket_map: Dict[str, Dict[str, Any]],
                     cost_for: Any = None, **factory: Any) -> List[Dict[str, Any]]:
                out = []
                for key, bucket in bucket_map.items():
                    extra = {k: fn(key) for k, fn in factory.items()}
                    if cost_for is not None:
                        extra.update(self._cost_over(cost_for(key, bucket)))
                    out.append(self._view(
                        key, bucket,
                        share_pct=round((bucket.get("total_tokens", 0) / grand) * 100, 1) if grand else 0.0,
                        **extra,
                    ))
                out.sort(key=lambda r: r["total_tokens"], reverse=True)
                return out

            return {
                "task_id": task["task_id"],
                "label": task.get("label", ""),
                "kind": task.get("kind", ""),
                "status": task.get("status", ""),
                "started_at": task.get("started_at"),
                "finished_at": task.get("finished_at"),
                "duration_s": task.get("duration_s"),
                "score": task.get("score"),
                "project_dir": task.get("project_dir"),
                "totals": {
                    **totals,
                    "avg_tokens_per_call": round(grand / totals["calls"]) if totals.get("calls") else 0,
                    **self._cost_over(model_buckets),
                },
                "by_provider": rows(
                    task.get("by_provider") or {},
                    cost_for=lambda k, b: [m for m in model_buckets if m.get("provider") == k],
                    provider=lambda k: k,
                    provider_label=lambda k: _provider_label(k),
                ),
                "by_model": rows(
                    task.get("by_model") or {},
                    cost_for=lambda k, b: [b],
                    model=lambda k: k,
                    model_name=lambda k: _model_meta(k).get("name") or k,
                    provider=lambda k: _model_meta(k).get("provider") or "—",
                ),
                "by_agent": [_without_cost(r) for r in rows(task.get("by_agent") or {}, agent=lambda k: k)],
                "calls": [
                    {**c, "cost_usd": self.estimate_cost(
                        c.get("model", ""), c.get("provider", ""),
                        c.get("prompt_tokens", 0), c.get("completion_tokens", 0))}
                    for c in list(reversed(task.get("calls") or []))[:200]
                ],
            }

    def task_usage_block(self, task_id: str) -> Dict[str, Any]:
        """
        `orchestration_completed` hodisasiga qo'shiladigan ixcham blok —
        foydalanuvchi natija bilan birga "bu vazifa qancha tokenga tushdi"ni ko'radi.
        """
        detail = self.task_detail(task_id)
        if not detail:
            return {}
        return {
            "task_id": task_id,
            "totals": detail["totals"],
            "by_provider": [
                {k: r[k] for k in ("provider", "provider_label", "calls", "prompt_tokens",
                                   "completion_tokens", "total_tokens", "cost_usd", "cost_known", "share_pct")}
                for r in detail["by_provider"]
            ],
            "by_model": [
                {k: r[k] for k in ("model", "model_name", "provider", "calls", "prompt_tokens",
                                   "completion_tokens", "total_tokens", "cost_usd", "cost_known", "share_pct")}
                for r in detail["by_model"]
            ],
            "by_agent": [
                {k: r[k] for k in ("agent", "calls", "prompt_tokens", "completion_tokens",
                                   "total_tokens", "share_pct")}
                for r in detail["by_agent"]
            ],
        }

    def export_csv(self, task_id: Optional[str] = None) -> str:
        """Chaqiruvlar jurnalini CSV ko'rinishida beradi (buxgalteriya/hisobot uchun)."""
        fields = [
            "ts", "task_id", "task_label", "agent", "role", "phase", "provider", "model",
            "prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens",
            "tokens_saved", "duration_ms", "cached", "success", "cost_usd",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()

        with self._lock:
            if task_id:
                task = self.tasks.get(task_id)
                source: List[Dict[str, Any]] = []
                for call in (task or {}).get("calls", []):
                    source.append({**call, "task_id": task_id, "task_label": (task or {}).get("label", "")})
            else:
                # Diskdagi jurnal — asosiy manba: server qayta ishga tushgach ham
                # eksport bo'sh qolmaydi. Xotiradagi ro'yxat faqat zaxira.
                source = self.read_call_log(limit=MAX_CALL_LINES) or list(self.recent_calls)

        for rec in source:
            row = dict(rec)
            row["ts"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec.get("ts") or 0))
            writer.writerow(row)
        return buf.getvalue()

    def read_call_log(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Diskdagi chaqiruvlar jurnalini o'qiydi (arxiv + joriy fayl).

        Faylning oxirgi `limit` yozuvi qaytariladi; buzuq satrlar sukut bilan
        tashlab yuboriladi — telemetriya hech qachon xatolik keltirmasligi kerak.
        """
        records: List[Dict[str, Any]] = []
        for path in (self.calls_archive, self.calls_file):
            try:
                if not path.exists():
                    continue
                with path.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            records.append(json.loads(line))
                        except ValueError:
                            continue
            except OSError:
                continue
        return records[-max(1, int(limit or 500)):]

    def reset(self) -> None:
        """Butun statistikani tozalaydi (foydalanuvchi so'rasa)."""
        with self._lock:
            self.by_provider.clear()
            self.by_model.clear()
            self.by_provider_model.clear()
            self.by_agent.clear()
            self.tasks.clear()
            self.recent_calls.clear()
            self.totals = _empty_bucket()
            self.started_at = time.time()
            self._line_count_cache = 0
            for path in (self.calls_file, self.calls_archive):
                try:
                    path.unlink()
                except OSError:
                    pass
            self._flush(force=True)


usage_ledger = UsageLedger()


def new_task_id(prefix: str = "task") -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
