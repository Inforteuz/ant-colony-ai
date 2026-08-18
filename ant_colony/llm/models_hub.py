"""
Models Hub: Real-time health monitoring, Background Auto-Pinger, Google Gemini & OpenAI pinging, and Prompt Caching integration.
"""
import time
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional
from ant_colony.config import PROVIDERS, MODELS_CATALOG, WORKSPACE_DIR, PROJECTS_BASE_DIR, AGENT_CONFIG
from ant_colony.llm.prompt_cache import prompt_cache

class ModelsHub:
    # Circuit breaker: shu miqdor ketma-ket xatolikdan keyin model vaqtinchalik
    # zaxira zanjiridan chetlanadi.
    CIRCUIT_FAIL_THRESHOLD = 3
    CIRCUIT_OPEN_SECONDS = 45.0
    # Provayder darajasidagi cooldown standart davomiyligi (429 uchun).
    PROVIDER_COOLDOWN_DEFAULT = 20.0
    # 401/403 uchun uzun cooldown — kalit almashtirilmasa foyda yo'q.
    PROVIDER_COOLDOWN_AUTH = 900.0

    def __init__(self):
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.bg_task: Optional[asyncio.Task] = None
        # Fon monitoringi navbat bilan tekshirish uchun kursor — hamma modelni
        # har daqiqada urish bepul kvotani yoqib yuborardi va ish vaqtida 429 keltirardi.
        self._monitor_cursor: int = 0
        # Orkestratsiya davomida fon pinglari to'xtatiladi (kvota agentlarga kerak).
        self.busy_until: float = 0.0
        # provider_id -> unix ts (shu vaqtgacha provayder ishlatilmaydi).
        # Butun provayder 429 yoki 401 qaytarsa, undagi barcha modellar chetlanadi.
        self.provider_cooldowns: Dict[str, float] = {}
        # Provayder tarixi — telemetriya uchun.
        self.provider_last_failure: Dict[str, str] = {}
        self.telemetry = {
            "total_llm_calls": 0,
            "total_tasks_run": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_reasoning_tokens": 0,
            "active_agents_count": 7,
            "start_time": time.time()
        }
        for m in MODELS_CATALOG:
            self.stats[m["id"]] = {
                "id": m["id"],
                "name": m["name"],
                "provider": m["provider"],
                "context_window": m["context_window"],
                "max_output": m["max_output"],
                "features": m["features"],
                "supports_reasoning": m["supports_reasoning"],
                # Tekshirilmagan model "online" deb ko'rsatilmaydi — model tanlash
                # endi shu maydonga tayanadi, yolg'on optimizm noto'g'ri tanlovga olib keladi.
                "status": "unknown",
                "latency_ms": 0,
                "uptime_pct": 0.0,
                "total_checks": 0,
                "success_checks": 0,
                "last_checked": None,
                "last_error": None,
                "history": [],
                # Circuit breaker: ketma-ket xatoliklar soni va qachongacha bloklangani.
                "consecutive_failures": 0,
                "circuit_open_until": 0.0,
                # Token sarfi — record_usage() to'ldiradi. Boshidanoq mavjud bo'lsin,
                # aks holda API javobida maydon umuman bo'lmaydi va UI "undefined" ko'rsatadi.
                "tokens_prompt": 0,
                "tokens_completion": 0,
                "tokens_total": 0,
            }

    def record_usage(self, prompt_tokens: int, completion_tokens: int, reasoning_tokens: int = 0, model_id: Optional[str] = None):
        self.telemetry["total_llm_calls"] += 1
        self.telemetry["total_prompt_tokens"] += prompt_tokens
        self.telemetry["total_completion_tokens"] += completion_tokens
        self.telemetry["total_reasoning_tokens"] += reasoning_tokens

        if model_id and model_id in self.stats:
            st = self.stats[model_id]
            st["tokens_prompt"] = st.get("tokens_prompt", 0) + prompt_tokens
            st["tokens_completion"] = st.get("tokens_completion", 0) + completion_tokens
            st["tokens_total"] = st.get("tokens_total", 0) + prompt_tokens + completion_tokens
            st["call_count"] = st.get("call_count", 0) + 1

    def record_task_completed(self):
        """Bitta orkestratsiya (foydalanuvchi topshirig'i) yakunlandi."""
        self.telemetry["total_tasks_run"] += 1

    def mark_busy(self, seconds: float = 300.0):
        """Agentlar ishlayotganda fon pinglarini to'xtatib turadi."""
        self.busy_until = max(self.busy_until, time.time() + seconds)

    def clear_busy(self):
        self.busy_until = 0.0

    def _update_health(self, model_id: str, status: str, latency_ms: int,
                       status_code: int = 0, error_msg: Optional[str] = None):
        """Sog'liq statistikasini yangilaydi (ping ham, real chaqiruv ham shu yerga tushadi)."""
        current = self.stats.get(model_id)
        if current is None:
            return
        total = current.get("total_checks", 0) + 1
        success = current.get("success_checks", 0) + (1 if status == "online" else 0)
        history = (current.get("history", []) + [{
            "timestamp": time.time(), "status": status,
            "status_code": status_code, "latency_ms": latency_ms
        }])[-15:]
        current.update({
            "status": status,
            "status_code": status_code,
            "latency_ms": latency_ms if latency_ms > 0 else current.get("latency_ms", 0),
            "uptime_pct": round((success / total) * 100, 1),
            "total_checks": total,
            "success_checks": success,
            "last_checked": time.time(),
            "last_error": error_msg,
            "history": history
        })

    def note_live_success(self, model_id: str, latency_ms: int):
        """
        Haqiqiy ish chaqiruvi muvaffaqiyatli o'tdi — bu sun'iy ping'dan ishonchliroq
        signal, shuning uchun sog'liq holatini bepul yangilaymiz.
        Circuit'ni yopamiz va provayder cooldown'ini tozalaymiz.
        """
        self._update_health(model_id, "online", latency_ms, 200, None)
        stat = self.stats.get(model_id)
        if stat:
            stat["consecutive_failures"] = 0
            stat["circuit_open_until"] = 0.0
        # Muvaffaqiyat — provayder tirik, cooldown mavjud bo'lsa olib tashlaymiz.
        prov = self._provider_of(model_id)
        if prov and prov in self.provider_cooldowns:
            self.provider_cooldowns.pop(prov, None)

    def note_live_failure(self, model_id: str, status_code: int,
                          retry_after: Optional[float] = None):
        """
        Haqiqiy ish chaqiruvi muvaffaqiyatsiz — modelni zaxira zanjiridan chetlatish uchun.
        Provayder darajasidagi cooldown va per-model circuit breaker'ni ham yangilaydi.
        """
        if status_code == 429:
            status, msg = "rate_limited", "Limit (429)"
        elif status_code in (500, 502, 503, 504, 529):
            status, msg = "degraded", f"Server band ({status_code})"
        elif status_code == 408:
            status, msg = "timeout", "Vaqt tugadi"
        elif status_code in (401, 403):
            status, msg = "error", f"Auth xato ({status_code})"
        else:
            status, msg = "error", f"HTTP {status_code}"
        self._update_health(model_id, status, 0, status_code, msg)

        stat = self.stats.get(model_id)
        if stat:
            stat["consecutive_failures"] = stat.get("consecutive_failures", 0) + 1
            if stat["consecutive_failures"] >= self.CIRCUIT_FAIL_THRESHOLD:
                stat["circuit_open_until"] = time.time() + self.CIRCUIT_OPEN_SECONDS

        prov = self._provider_of(model_id)
        if not prov:
            return
        now = time.time()
        if status_code in (401, 403):
            # Kalit noto'g'ri yoki cheklangan — butun provayder foydasiz.
            self.provider_cooldowns[prov] = now + self.PROVIDER_COOLDOWN_AUTH
            self.provider_last_failure[prov] = f"auth {status_code}"
        elif status_code == 429:
            cd = retry_after if (retry_after and retry_after > 0) else self.PROVIDER_COOLDOWN_DEFAULT
            self.provider_cooldowns[prov] = max(self.provider_cooldowns.get(prov, 0.0), now + min(cd, 120.0))
            self.provider_last_failure[prov] = "rate limit"
        elif status_code in (500, 502, 503, 504, 529):
            # Yengil cooldown — server tiklanishi mumkin.
            self.provider_cooldowns[prov] = max(self.provider_cooldowns.get(prov, 0.0), now + 8.0)
            self.provider_last_failure[prov] = f"server {status_code}"

    def _provider_of(self, model_id: str) -> Optional[str]:
        stat = self.stats.get(model_id)
        return (stat or {}).get("provider")

    def is_provider_configured(self, provider_id: str,
                               custom_keys: Optional[Dict[str, str]] = None) -> bool:
        """
        Provayderda API kalit bormi?

        MUHIM: ilgari bu tekshiruv umuman yo'q edi. Bitta provayder kalitiga ega
        foydalanuvchida ham zaxira zanjiri BARCHA kataloglardagi modellar bilan
        to'ldirilardi — har so'rovda kalitsiz provayderlarga 401/403 so'rov ketib,
        vaqt va urinishlar bekorga sarflanardi. Endi kalitsiz provayder umuman
        tanlanmaydi.
        """
        if custom_keys and custom_keys.get(provider_id):
            return True
        return bool((PROVIDERS.get(provider_id) or {}).get("default_key", "").strip())

    def configured_providers(self) -> List[str]:
        """Kaliti mavjud provayderlar ro'yxati (diagnostika va UI uchun)."""
        return [pid for pid in PROVIDERS if self.is_provider_configured(pid)]

    def is_provider_available(self, provider_id: str) -> bool:
        """Provayder hozir ishlatilishi mumkinmi?"""
        # Kalitsiz provayder hech qachon ishlatilmaydi.
        if not self.is_provider_configured(provider_id):
            return False
        deadline = self.provider_cooldowns.get(provider_id, 0.0)
        if deadline <= 0:
            return True
        if time.time() >= deadline:
            self.provider_cooldowns.pop(provider_id, None)
            return True
        return False

    def is_model_available(self, model_id: str) -> bool:
        """Model circuit ochiq bo'lsa yoki provayderi cooldown'da bo'lsa — mavjud emas."""
        stat = self.stats.get(model_id)
        if not stat:
            return False
        now = time.time()
        if stat.get("circuit_open_until", 0.0) > now:
            return False
        prov = stat.get("provider")
        return self.is_provider_available(prov) if prov else True

    def provider_cooldown_snapshot(self) -> Dict[str, float]:
        """Faol cooldownlar (foydali tashxis uchun)."""
        now = time.time()
        return {p: round(t - now, 1) for p, t in self.provider_cooldowns.items() if t > now}

    def _workspace_footprint(self, ttl: float = 15.0) -> tuple:
        """
        Aktiv loyiha va ishchi muhitdagi fayl soni va hajmi (chegaralangan, keshlangan).
        """
        now = time.time()
        cached = getattr(self, "_footprint_cache", None)
        if cached and (now - cached[0]) < ttl:
            return cached[1], cached[2]

        # Import shu yerda — modul yuklanish tartibida aylanma bog'liqlik bo'lmasligi uchun.
        from ant_colony.runtime.tools import walk_project_files, get_active_project_dir

        file_count = 0
        total_bytes = 0
        seen = set()
        for root in (get_active_project_dir(), WORKSPACE_DIR):
            if not root or not root.exists():
                continue
            found, _ = walk_project_files(root, limit=1000)
            for path, _rel in found:
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    total_bytes += path.stat().st_size
                    file_count += 1
                except Exception:
                    continue

        self._footprint_cache = (now, file_count, total_bytes)
        return file_count, total_bytes

    def get_real_hive_stats(self) -> Dict[str, Any]:
        """Compute real, authentic stats from system, Desktop projects, and Prompt Cache."""
        total_models = len(self.stats)
        online_models = len([m for m in self.stats.values() if m["status"] == "online"])
        checked_models = len([m for m in self.stats.values() if m.get("total_checks", 0) > 0])

        valid_latencies = [m["latency_ms"] for m in self.stats.values() if m["latency_ms"] > 0]
        avg_latency = round(sum(valid_latencies) / len(valid_latencies)) if valid_latencies else 0

        # Fayl statistikasi. Ilgari bu yerda `PROJECTS_BASE_DIR.rglob("*")` bor edi
        # va HAR BIR stats so'rovida butun loyihalar daraxti (600 mingdan ortiq
        # fayl, o'nlab GB) aylanib chiqilardi — interfeys shu sababli osilib qolardi.
        # Endi: chegaralangan aylanish + qisqa muddatli kesh.
        file_count, total_bytes = self._workspace_footprint()

        total_tokens = self.telemetry["total_prompt_tokens"] + self.telemetry["total_completion_tokens"]
        cache_stats = prompt_cache.get_stats()

        # Dynamic health computation based on real live data.
        # Nisbat *tekshirilgan* modellarga qarab hisoblanadi — hali sinalmagan
        # modellarni "tushib qolgan" deb ko'rsatish noto'g'ri xulosa berardi.
        if checked_models == 0:
            return {
                "total_models": total_models, "online_models": 0,
                "checked_models": 0,
                "health_status": "Tekshirilmoqda...", "health_level": 2,
                "health_color": "#f59e0b",
                "total_tasks_run": self.telemetry["total_tasks_run"],
                "total_llm_calls": self.telemetry["total_llm_calls"],
                "total_tokens_consumed": total_tokens,
                "prompt_tokens": self.telemetry["total_prompt_tokens"],
                "completion_tokens": self.telemetry["total_completion_tokens"],
                "reasoning_tokens": self.telemetry["total_reasoning_tokens"],
                "workspace_files_count": file_count, "workspace_bytes": total_bytes,
                "avg_latency_ms": avg_latency, "prompt_cache": cache_stats,
                "desktop_projects_path": str(PROJECTS_BASE_DIR),
                "system_health": "Tekshirilmoqda..."
            }

        online_ratio = online_models / checked_models
        if online_ratio >= 0.95 and 0 < avg_latency <= 1000:
            health_status = f"A'lo ({online_models}/{checked_models} onlayn)"
            health_level = 4
            health_color = "#10b981"  # emerald
        elif online_ratio >= 0.70:
            health_status = f"Yaxshi ({online_models}/{checked_models} onlayn)"
            health_level = 3
            health_color = "#06b6d4"  # cyan
        elif online_ratio >= 0.40:
            health_status = f"O'rtacha ({online_models}/{checked_models} onlayn)"
            health_level = 2
            health_color = "#f59e0b"  # amber
        else:
            health_status = f"Cheklangan ({online_models}/{checked_models} onlayn)"
            health_level = 1
            health_color = "#ef4444"  # red

        return {
            "total_models": total_models,
            "online_models": online_models,
            "checked_models": checked_models,
            "health_status": health_status,
            "health_level": health_level,
            "health_color": health_color,
            "total_tasks_run": self.telemetry["total_tasks_run"],
            "total_llm_calls": self.telemetry["total_llm_calls"],
            "total_tokens_consumed": total_tokens,
            "prompt_tokens": self.telemetry["total_prompt_tokens"],
            "completion_tokens": self.telemetry["total_completion_tokens"],
            "reasoning_tokens": self.telemetry["total_reasoning_tokens"],
            "workspace_files_count": file_count,
            "workspace_bytes": total_bytes,
            "avg_latency_ms": avg_latency,
            "prompt_cache": cache_stats,
            "desktop_projects_path": str(PROJECTS_BASE_DIR),
            "system_health": health_status
        }

    def get_api_key(self, provider_id: str, custom_keys: Optional[Dict[str, str]] = None) -> str:
        if custom_keys and provider_id in custom_keys and custom_keys[provider_id]:
            return custom_keys[provider_id]
        return PROVIDERS.get(provider_id, {}).get("default_key", "")

    async def ping_model(self, model_id: str, custom_keys: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        meta = next((m for m in MODELS_CATALOG if m["id"] == model_id), None)
        if not meta:
            return {"error": "Model topilmadi", "model_id": model_id}

        provider_id = meta["provider"]
        provider_info = PROVIDERS.get(provider_id, {})
        api_key = self.get_api_key(provider_id, custom_keys)

        # Kalit yo'q bo'lsa — so'rov yubormaymiz. Ilgari kalitsiz provayderlar ham
        # ping qilinib, UI'da "Ошибка" deb ko'rinardi va foydalanuvchi tizim buzuq
        # deb o'ylardi. To'g'ri holat: "не настроен".
        if not api_key or not api_key.strip():
            stat = self.stats.get(model_id)
            if stat is not None:
                stat.update({
                    "status": "not_configured",
                    "last_checked": time.time(),
                    "last_error": f"{provider_info.get('name', provider_id)}: API kalit kiritilmagan",
                })
            return {
                "model_id": model_id, "status": "not_configured",
                "latency_ms": 0, "status_code": 0,
                "error": "API kalit kiritilmagan",
            }

        t0 = time.time()
        status = "error"
        status_code = 0
        latency_ms = 0
        error_msg = None

        try:
            timeout = aiohttp.ClientTimeout(total=8, sock_connect=3, sock_read=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 1. Google Gemini API
                if provider_id == "gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": "ping"}]}], "generationConfig": {"maxOutputTokens": 5}}
                    async with session.post(url, json=payload) as resp:
                        latency_ms = round((time.time() - t0) * 1000)
                        status_code = resp.status
                        if resp.status == 200:
                            status = "online"
                        elif resp.status == 429:
                            status = "rate_limited"
                            error_msg = "Gemini limit (429)"
                        else:
                            status = "error"
                            error_msg = f"Gemini xato {resp.status}"

                # 2. OpenAI-compatible (17.wtf & OpenRouter)
                else:
                    url = f"{provider_info.get('base_url', '')}{provider_info.get('chat_endpoint', '/chat/completions')}"
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"model": model_id, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
                    async with session.post(url, headers=headers, json=payload) as resp:
                        latency_ms = round((time.time() - t0) * 1000)
                        status_code = resp.status
                        if resp.status == 200:
                            status = "online"
                        elif resp.status == 429:
                            status = "rate_limited"
                            error_msg = "Limit (429)"
                        elif resp.status in (502, 503, 504):
                            status = "degraded"
                            error_msg = f"Server band ({resp.status})"
                        else:
                            status = "error"
                            text = await resp.text()
                            error_msg = text[:120]
        except asyncio.TimeoutError:
            latency_ms = round((time.time() - t0) * 1000)
            status = "timeout"
            status_code = 408
            error_msg = "Vaqt tugadi (>8s)"
        except Exception as e:
            latency_ms = round((time.time() - t0) * 1000)
            status = "error"
            error_msg = str(e)[:120]

        self._update_health(model_id, status, latency_ms, status_code, error_msg)
        return self.stats[model_id]

    async def ping_all_models(self, custom_keys: Optional[Dict[str, str]] = None,
                             model_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        sem = asyncio.Semaphore(3)
        async def bounded_ping(m_id):
            async with sem:
                return await self.ping_model(m_id, custom_keys)

        targets = model_ids or [m["id"] for m in MODELS_CATALOG]
        tasks = [bounded_ping(m_id) for m_id in targets]
        await asyncio.gather(*tasks, return_exceptions=True)
        return list(self.stats.values())

    def get_all_stats(self) -> List[Dict[str, Any]]:
        return list(self.stats.values())

    async def background_monitor_loop(self):
        """
        Modellarni fonda navbat bilan, kichik guruhlarda tekshiradi.

        Ilgari har 60 sekundda 14 ta modelga real API chaqiruvi ketardi — bu bepul
        kvotani kuniga ~20 ming so'rovga yoqib, aynan agentlar ishlayotgan paytda
        429 xatoliklarini keltirib chiqarardi. Endi:
          * oralig'i uzoq (default 10 daqiqa);
          * bir raundda faqat bir necha model (aylanma navbat);
          * orkestratsiya davomida umuman to'xtaydi — kvota agentlarga qoladi;
          * haqiqiy ish chaqiruvlari ham sog'liqni yangilaydi (note_live_success),
            shuning uchun faol modellarni alohida ping qilish shart emas.
        """
        await asyncio.sleep(10)  # Allow server to start up smoothly first
        catalog_ids = [m["id"] for m in MODELS_CATALOG]
        interval = AGENT_CONFIG["health_monitor_interval_s"]
        batch_size = max(1, AGENT_CONFIG["health_monitor_batch"])

        while True:
            try:
                if time.time() < self.busy_until:
                    # Agentlar ishlamoqda — kvotani ular uchun saqlaymiz.
                    await asyncio.sleep(30)
                    continue

                fresh_cutoff = time.time() - interval
                batch = []
                for _ in range(len(catalog_ids)):
                    m_id = catalog_ids[self._monitor_cursor % len(catalog_ids)]
                    self._monitor_cursor += 1
                    last = self.stats.get(m_id, {}).get("last_checked")
                    # Yaqinda (haqiqiy ish chaqirig'i orqali ham) tekshirilganini o'tkazib yuboramiz.
                    if last is None or last < fresh_cutoff:
                        batch.append(m_id)
                    if len(batch) >= batch_size:
                        break

                if batch:
                    await self.ping_all_models(model_ids=batch)
            except Exception:
                pass
            await asyncio.sleep(max(30, interval // max(1, len(catalog_ids) // batch_size)))

    def start_background_monitor(self):
        if not self.bg_task or self.bg_task.done():
            try:
                self.bg_task = asyncio.create_task(self.background_monitor_loop())
            except Exception:
                pass

    async def fetch_models_from_provider(self, base_url: str, api_key: str = "") -> Dict[str, Any]:
        """Dynamically fetches the list of available models from any OpenAI-compatible or Ollama endpoint."""
        url = base_url.strip().rstrip("/")
        if not url:
            return {"success": False, "error": "Base URL не может быть пустым"}

        if not url.endswith("/models") and not url.endswith("/api/tags"):
            if "ollama" in url or ":11434" in url:
                models_url = f"{url}/api/tags" if not url.endswith("/api") else f"{url}/tags"
            else:
                models_url = f"{url}/models" if url.endswith("/v1") else f"{url}/v1/models"
        else:
            models_url = url

        headers = {
            "User-Agent": "AntColonyAI/3.0",
            "Accept": "application/json"
        }
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        t0 = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as session:
                async with session.get(models_url, headers=headers) as resp:
                    latency_ms = int((time.time() - t0) * 1000)
                    if resp.status != 200:
                        err_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"HTTP {resp.status}: {err_text[:300]}",
                            "latency_ms": latency_ms
                        }
                    data = await resp.json()
                    raw_models = []
                    # Standard OpenAI format: {"data": [{"id": "..."}, ...]}
                    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                        raw_models = data["data"]
                    # Ollama format: {"models": [{"name": "..."}, ...]}
                    elif isinstance(data, dict) and "models" in data and isinstance(data["models"], list):
                        raw_models = data["models"]
                    elif isinstance(data, list):
                        raw_models = data

                    parsed = []
                    for item in raw_models:
                        if isinstance(item, dict):
                            m_id = item.get("id") or item.get("name") or item.get("model")
                            m_name = item.get("name") or item.get("id") or m_id
                            if m_id:
                                parsed.append({
                                    "id": str(m_id),
                                    "name": str(m_name),
                                    "provider": "custom",
                                    "owned_by": item.get("owned_by", "custom"),
                                    "context_length": item.get("context_length", 32768)
                                })
                        elif isinstance(item, str):
                            parsed.append({
                                "id": item,
                                "name": item,
                                "provider": "custom"
                            })

                    return {
                        "success": True,
                        "url": models_url,
                        "latency_ms": latency_ms,
                        "count": len(parsed),
                        "models": parsed
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": int((time.time() - t0) * 1000)
            }

    def register_custom_provider(self, base_url: str, api_key: str, models: List[Dict[str, Any]]):
        """Registers discovered custom models into the runtime catalog and monitoring state."""
        PROVIDERS["custom"] = {
            "name": "Custom Provider / Ollama",
            "base_url": base_url,
            "default_key": api_key
        }
        for m in models:
            m_id = m["id"]
            if m_id not in self.stats:
                model_entry = {
                    "id": m_id,
                    "name": m.get("name") or m_id,
                    "provider": "custom",
                    "context_window": m.get("context_length") or 32768,
                    "max_output": 8192,
                    "features": ["code", "chat", "custom"],
                    "supports_reasoning": False
                }
                MODELS_CATALOG.append(model_entry)
                self.stats[m_id] = {
                    **model_entry,
                    "status": "online",
                    "latency_ms": 45,
                    "uptime_pct": 100.0,
                    "total_checks": 1,
                    "success_checks": 1,
                    "last_checked": time.time(),
                    "last_error": None,
                    "history": []
                }

models_hub = ModelsHub()
