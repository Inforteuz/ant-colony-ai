"""
Prompt Caching Layer for Ant Colony AI Platform.

Faqat DETERMINISTIK chaqiruvlar keshlanadi (temperature == 0, asboblarsiz) —
bu tekshiruvni `llm_client` bajaradi. Ilgari kesh barcha chaqiruvlarga, hatto
ijodiy kod generatsiyasiga ham qo'llanardi: natijada agent 7 kun davomida bir
xil eski javobni qaytarib, hech qanday yangi kod yozmasdi.

Boshqa tuzatilgan muammolar:
  * har `set()` da butun kesh fayli diskka yozilardi (O(n) I/O har LLM chaqirig'ida)
    — endi yozish debounce qilinadi;
  * kesh cheksiz o'sardi — endi LRU chegarasi bor;
  * eski (TTL o'tgan) yozuvlar faqat o'qishda o'chirilardi — endi yuklashda tozalanadi.
"""
import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Any, Optional
from ant_colony.config import DATA_DIR

CACHE_FILE = DATA_DIR / "prompt_cache.json"

MAX_ENTRIES = 400
# Diskka yozishni shu qadar sekunddan tez-tez qilmaymiz.
FLUSH_INTERVAL_S = 20.0
# Shuncha yangi yozuvdan keyin majburiy yozish.
FLUSH_EVERY_N_SETS = 25


class PromptCache:
    def __init__(self, ttl_seconds: int = 86400 * 7):  # 7 days TTL
        self.ttl = ttl_seconds
        self.cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "tokens_saved": 0,
            "evictions": 0,
            "last_hit_time": None,
            # Model kesimida tejamkorlik: {model_id: {"hits": n, "tokens_saved": n}}
            # UI'da "qaysi model qancha token tejadi" ni ko'rsatish uchun.
            "by_model": {}
        }
        self._dirty_count = 0
        self._last_flush = 0.0
        self.load_cache()

    def _generate_key(self, model_id: str, messages: list) -> str:
        serialized = json.dumps({"model": model_id, "messages": messages}, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, model_id: str, messages: list) -> Optional[Dict[str, Any]]:
        key = self._generate_key(model_id, messages)
        entry = self.cache.get(key)
        if not entry:
            self.stats["misses"] += 1
            return None

        if time.time() - entry["timestamp"] > self.ttl:
            self.cache.pop(key, None)
            self.stats["misses"] += 1
            return None

        # LRU: ishlatilgan yozuvni oxiriga suramiz.
        self.cache.move_to_end(key)

        self.stats["hits"] += 1
        self.stats["last_hit_time"] = time.time()
        tokens_saved = entry.get("tokens_saved", 0)
        self.stats["tokens_saved"] += tokens_saved

        entry_model = entry.get("model_id") or model_id or "unknown"
        per_model = self.stats.setdefault("by_model", {})
        bucket = per_model.setdefault(entry_model, {"hits": 0, "tokens_saved": 0})
        bucket["hits"] += 1
        bucket["tokens_saved"] += tokens_saved

        return {
            "cached": True,
            "response": entry["response"],
            "tokens_saved": tokens_saved,
            "cached_at": entry["timestamp"]
        }

    def set(self, model_id: str, messages: list, response: Dict[str, Any], tokens_saved: int = 0):
        key = self._generate_key(model_id, messages)
        self.cache[key] = {
            "model_id": model_id,
            "timestamp": time.time(),
            "response": response,
            "tokens_saved": tokens_saved
        }
        self.cache.move_to_end(key)

        while len(self.cache) > MAX_ENTRIES:
            self.cache.popitem(last=False)  # eng eski ishlatilgani
            self.stats["evictions"] += 1

        self._dirty_count += 1
        now = time.time()
        if self._dirty_count >= FLUSH_EVERY_N_SETS or (now - self._last_flush) >= FLUSH_INTERVAL_S:
            self.save_cache()

    def invalidate_all(self) -> int:
        removed = len(self.cache)
        self.cache.clear()
        self.save_cache()
        return removed

    def get_stats(self) -> Dict[str, Any]:
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = round((self.stats["hits"] / total) * 100, 1) if total > 0 else 0.0

        # Model kesimi: real tejalgan (hit orqali) + hozir keshda turgan zaxira.
        by_model = {}
        for model_id, bucket in (self.stats.get("by_model") or {}).items():
            by_model[model_id] = {
                "model_id": model_id,
                "hits": bucket.get("hits", 0),
                "tokens_saved": bucket.get("tokens_saved", 0),
                "entries": 0,
                "cached_tokens": 0,
            }
        for entry in self.cache.values():
            model_id = entry.get("model_id") or "unknown"
            row = by_model.setdefault(model_id, {
                "model_id": model_id, "hits": 0, "tokens_saved": 0,
                "entries": 0, "cached_tokens": 0,
            })
            row["entries"] += 1
            row["cached_tokens"] += entry.get("tokens_saved", 0)

        breakdown = sorted(by_model.values(),
                           key=lambda r: (r["tokens_saved"], r["cached_tokens"]),
                           reverse=True)

        return {
            "total_cached_entries": len(self.cache),
            "max_entries": MAX_ENTRIES,
            "cache_hits": self.stats["hits"],
            "cache_misses": self.stats["misses"],
            "hit_rate_pct": hit_rate,
            "tokens_saved": self.stats["tokens_saved"],
            "evictions": self.stats["evictions"],
            "last_hit_time": self.stats["last_hit_time"],
            "by_model": breakdown
        }

    def load_cache(self):
        if not CACHE_FILE.exists():
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        raw = data.get("cache", {})
        now = time.time()
        # Yuklashda TTL o'tgan yozuvlarni tashlab yuboramiz.
        items = [(k, v) for k, v in raw.items()
                 if isinstance(v, dict) and (now - v.get("timestamp", 0)) <= self.ttl]
        items.sort(key=lambda kv: kv[1].get("timestamp", 0))
        self.cache = OrderedDict(items[-MAX_ENTRIES:])

        saved_stats = data.get("stats")
        if isinstance(saved_stats, dict):
            self.stats.update({k: v for k, v in saved_stats.items() if k in self.stats})

    def save_cache(self):
        try:
            tmp = CACHE_FILE.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"cache": dict(self.cache), "stats": self.stats},
                          f, ensure_ascii=False)
            tmp.replace(CACHE_FILE)  # atomik almashtirish — yarim yozilgan fayl qolmaydi
            self._dirty_count = 0
            self._last_flush = time.time()
        except Exception:
            pass


prompt_cache = PromptCache()
