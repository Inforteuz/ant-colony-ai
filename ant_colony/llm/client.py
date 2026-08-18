"""
Resilient LLM Client: native function-calling (Gemini + OpenAI-mos), provayderlar
o'rtasida ko'chirilishi mumkin bo'lgan yagona xabar formati, 429/5xx uchun
qayta urinish, sog'liq holatiga qarab tartiblangan zaxira modellar zanjiri.

Xabarlarning ichki (kanonik) formati provayderdan mustaqil:
    {"role": "system"|"user"|"assistant"|"tool",
     "content": str,
     "tool_calls": [{"id": str, "name": str, "arguments": dict}],   # faqat assistant
     "tool_call_id": str, "name": str}                              # faqat tool
Shu sababli suhbat o'rtasida boshqa provayderga o'tib ketsa ham tarix buzilmaydi.
"""
import json
import time
import random
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple

from ant_colony.config import PROVIDERS, MODELS_CATALOG, AGENT_CONFIG
from ant_colony.llm.models_hub import models_hub
from ant_colony.llm.prompt_cache import prompt_cache

# Zaxira zanjirining maksimal uzunligi — bitta chaqiruvda cheksiz urinmaslik uchun.
MAX_FALLBACK_MODELS = 4

# Sog'liq holatlarining afzallik tartibi (kichik son = yaxshiroq).
_STATUS_RANK = {
    "online": 0, "degraded": 1, "unknown": 2,
    "timeout": 3, "rate_limited": 4, "error": 5
}


def _model_meta(model_id: str) -> Dict[str, Any]:
    return next((m for m in MODELS_CATALOG if m["id"] == model_id), {})


def _provider_for(model_id: str) -> str:
    meta = _model_meta(model_id)
    if meta:
        return meta["provider"]
    return "gemini" if "gemini" in model_id else "17_wtf"


def _model_max_output(model_id: str, requested: Optional[int]) -> int:
    """Modelning haqiqiy chiqish limitidan oshib ketmaydi, lekin uni behuda cheklamaydi."""
    hard_cap = _model_meta(model_id).get("max_output", 8192)
    want = requested if requested else 8192
    return max(512, min(int(want), int(hard_cap), 32768))


def _adaptive_timeout(max_tokens: int) -> float:
    """Katta chiqish kutilayotganda timeout ham kattaroq bo'lishi kerak."""
    base = AGENT_CONFIG["llm_base_timeout_s"]
    return min(AGENT_CONFIG["llm_max_timeout_s"], base + max_tokens / 90.0)


def build_fallback_chain(primary: str, exclude: Optional[List[str]] = None) -> List[str]:
    """
    Zaxira modellar zanjirini models_hub'dagi *real* sog'liq ma'lumotidan quradi.
    Oldingi qattiq kodlangan ro'yxat o'lik modelga urinishda vaqt yo'qotardi.

    Yangi qoidalar:
      * Circuit ochiq (uzluksiz xatoliklar) — chetlanadi.
      * Provayder cooldown'da (429/401 tufayli) — undagi barcha modellar chetlanadi,
        lekin agar hech qanday modeldan iborat zanjir qolmasa, faqat cooldown'dagilardan
        eng erta tugaydigani qaytariladi (butun tizim o'lmasin).
      * Zanjirda kamida 2 xil provayder bo'lishga harakat qilamiz.
    """
    exclude = set(exclude or [])
    primary_available = models_hub.is_model_available(primary) and primary not in exclude
    chain = [primary] if primary_available else []
    used_providers = {_provider_for(primary)} if primary_available else set()

    healthy = []
    quarantined = []  # circuit ochiq yoki provayder cooldown'da — oxirgi choraga

    for m in MODELS_CATALOG:
        mid = m["id"]
        if mid == primary or mid in exclude:
            continue
        # Kaliti kiritilmagan provayder modellari zanjirga umuman kirmaydi.
        # Aks holda bitta provayderli o'rnatishda har chaqiruv 401 bilan
        # bir necha marta urinib, sekinlashib ketardi.
        if not models_hub.is_provider_configured(m["provider"]):
            continue
        stat = models_hub.stats.get(mid, {})
        status = stat.get("status", "unknown")
        prov = m["provider"]
        entry = (
            _STATUS_RANK.get(status, 2),
            stat.get("latency_ms", 5000),
            0 if prov != _provider_for(primary) else 1,
            mid,
            prov,
        )
        if not models_hub.is_model_available(mid) or status in ("error",):
            quarantined.append(entry)
        else:
            healthy.append(entry)

    healthy.sort(key=lambda x: (x[0], x[2], x[1]))

    # Birinchi bosqich: har qadamda hali ishlatilmagan provayderdan eng yaxshi modelni
    # olamiz (round-robin). Ilgari "diverse" ro'yxati sikldan OLDIN bir marta
    # hisoblanardi — natijada bitta provayderning bir nechta modeli zanjirni to'ldirib,
    # boshqa provayderlar umuman tushmay qolardi (provayder tushib qolsa zanjir foydasiz).
    remaining = list(healthy)
    while remaining and len(chain) < MAX_FALLBACK_MODELS:
        pick = next((c for c in remaining if c[4] not in used_providers), remaining[0])
        remaining.remove(pick)
        chain.append(pick[3])
        used_providers.add(pick[4])

    # Ikkinchi bosqich: agar zanjir bo'sh bo'lsa (hamma model quarantine'da) —
    # eng erta tiklanadiganini yakuniy chora sifatida qo'shamiz.
    if not chain and quarantined:
        quarantined.sort(key=lambda x: x[1])
        chain.append(quarantined[0][3])

    return chain[:MAX_FALLBACK_MODELS]


def _parse_retry_after(headers) -> Optional[float]:
    """`Retry-After` sarlavhasini soniyaga aylantiradi (raqam yoki HTTP-date)."""
    if headers is None:
        return None
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(raw)
            if dt is None:
                return None
            return max(0.0, dt.timestamp() - time.time())
        except Exception:
            return None


# --- Provayderga xos konvertorlar ---

def _to_openai_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for m in messages:
        role = m.get("role", "user")
        if role == "tool":
            out.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", m.get("name", "call_0")),
                "content": m.get("content", "")
            })
            continue
        entry: Dict[str, Any] = {"role": role, "content": m.get("content", "") or ""}
        if role == "assistant" and m.get("tool_calls"):
            entry["tool_calls"] = [{
                "id": tc.get("id", f"call_{i}"),
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc.get("arguments", {}), ensure_ascii=False)
                }
            } for i, tc in enumerate(m["tool_calls"])]
            # OpenAI sxemasi tool_calls bilan bo'sh content'ni qabul qiladi.
            if not entry["content"]:
                entry["content"] = None
        out.append(entry)
    return out


def _to_gemini_payload(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Kanonik xabarlarni Gemini `contents` + `systemInstruction` ga aylantiradi."""
    system_parts = [m.get("content", "") for m in messages if m.get("role") == "system" and m.get("content")]
    contents: List[Dict[str, Any]] = []

    for m in messages:
        role = m.get("role")
        if role == "system":
            continue

        if role == "tool":
            payload_obj: Any
            try:
                payload_obj = json.loads(m.get("content", "{}"))
            except Exception:
                payload_obj = {"output": m.get("content", "")}
            if not isinstance(payload_obj, dict):
                payload_obj = {"output": payload_obj}
            part = {"functionResponse": {"name": m.get("name", "tool"), "response": payload_obj}}
            if contents and contents[-1]["role"] == "user":
                contents[-1]["parts"].append(part)
            else:
                contents.append({"role": "user", "parts": [part]})
            continue

        g_role = "user" if role == "user" else "model"
        parts: List[Dict[str, Any]] = []
        if m.get("content"):
            parts.append({"text": m["content"]})
        for tc in m.get("tool_calls") or []:
            parts.append({"functionCall": {"name": tc["name"], "args": tc.get("arguments", {})}})
        if not parts:
            continue

        if contents and contents[-1]["role"] == g_role:
            contents[-1]["parts"].extend(parts)
        else:
            contents.append({"role": g_role, "parts": parts})

    if not contents:
        contents = [{"role": "user", "parts": [{"text": "Boshlang"}]}]

    return contents, ("\n\n".join(system_parts) if system_parts else None)


def _parse_openai_response(res_json: Dict[str, Any]) -> Dict[str, Any]:
    choice = (res_json.get("choices") or [{}])[0]
    msg = choice.get("message", {}) or {}
    text = msg.get("content") or ""

    reasoning = ""
    for key in ("reasoning", "reasoning_content", "thinking"):
        val = msg.get(key)
        if isinstance(val, str) and val.strip():
            reasoning = val
            break
    details = msg.get("reasoning_details")
    if not reasoning and details:
        if isinstance(details, dict):
            reasoning = details.get("text", "") or ""
        elif isinstance(details, list):
            reasoning = "\n".join(
                d.get("text", "") for d in details if isinstance(d, dict)
            ).strip()

    tool_calls = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        fn = tc.get("function", {}) or {}
        raw_args = fn.get("arguments", "{}")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except Exception:
            args = {"_raw": raw_args}
        if fn.get("name"):
            tool_calls.append({
                "id": tc.get("id", f"call_{i}"),
                "name": fn["name"],
                "arguments": args if isinstance(args, dict) else {}
            })

    return {"text": text, "reasoning": reasoning, "tool_calls": tool_calls,
            "finish_reason": choice.get("finish_reason", "")}


def _parse_gemini_response(res_json: Dict[str, Any]) -> Dict[str, Any]:
    candidates = res_json.get("candidates") or []
    if not candidates:
        return {"text": "", "reasoning": "", "tool_calls": [], "finish_reason": "empty"}

    cand = candidates[0]
    parts = (cand.get("content") or {}).get("parts") or []
    texts, thoughts, tool_calls = [], [], []

    for i, p in enumerate(parts):
        if "functionCall" in p:
            fc = p["functionCall"]
            tool_calls.append({
                "id": f"call_{i}",
                "name": fc.get("name", ""),
                "arguments": fc.get("args") or {}
            })
        elif "text" in p:
            (thoughts if p.get("thought") else texts).append(p["text"])

    return {
        "text": "\n".join(texts).strip(),
        "reasoning": "\n".join(thoughts).strip(),
        "tool_calls": [tc for tc in tool_calls if tc["name"]],
        "finish_reason": cand.get("finishReason", "")
    }


class LLMClient:
    """Barcha provayderlar uchun yagona, chidamli kirish nuqtasi."""

    async def complete(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        custom_keys: Optional[Dict[str, str]] = None,
        exclude_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Bitta LLM chaqiruvi. Muvaffaqiyatsizlikda sog'lom modellarga o'tadi.
        Prompt Caching deterministik va tizimli so'rovlarni avtomatik keshlaydi.
        """
        cacheable = use_cache and (temperature <= 0.4 or not tools)

        if cacheable:
            cached = prompt_cache.get(model_id, messages)
            if cached:
                resp = cached["response"]
                models_hub.telemetry["total_llm_calls"] += 1
                return {
                    "success": True,
                    "text": resp.get("text", ""),
                    "reasoning": resp.get("reasoning", ""),
                    "tool_calls": resp.get("tool_calls", []),
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                              "cached_tokens_saved": cached.get("tokens_saved", 0)},
                    "model_used": model_id, "provider": "cache",
                    "duration_ms": 1, "cached": True,
                    "fallback_used": False, "attempts": []
                }

        chain = build_fallback_chain(model_id, exclude=exclude_models)
        attempts: List[Dict[str, Any]] = []
        last_error = "Неизвестная ошибка"

        # Hech qanday provayder sozlanmagan bo'lsa — tushunarli xabar qaytaramiz.
        # Ilgari bu holat "Неизвестная ошибка" bo'lib chiqar, foydalanuvchi nimani
        # tuzatish kerakligini bilmasdi.
        if not chain:
            configured = models_hub.configured_providers()
            if not configured:
                msg = ("Ни один провайдер не настроен: добавьте хотя бы один API-ключ "
                       "(Настройки → Setup Wizard) или пропишите его в файле .env.")
            else:
                msg = (f"Нет доступных моделей. Настроены провайдеры: {', '.join(configured)}. "
                       "Возможно, все их модели временно в лимите (429) — попробуйте позже "
                       "или добавьте второго провайдера.")
            return {
                "success": False, "text": "", "reasoning": "", "tool_calls": [],
                "error": msg, "needs_setup": not configured,
                "model_used": None, "provider": None,
                "duration_ms": 0, "fallback_used": False, "attempts": [],
            }

        for m_id in chain:
            provider_id = _provider_for(m_id)
            effective_max = _model_max_output(m_id, max_tokens)
            timeout_s = _adaptive_timeout(effective_max)
            retries = AGENT_CONFIG["llm_retries_per_model"]

            for attempt in range(retries + 1):
                t0 = time.time()
                try:
                    result = await self._call_provider(
                        provider_id, m_id, messages, tools,
                        temperature, effective_max, timeout_s, custom_keys
                    )
                except asyncio.TimeoutError:
                    last_error = f"{m_id}: timeout (>{int(timeout_s)}s)"
                    attempts.append({"model": m_id, "error": "timeout"})
                    break  # timeout'da qayta urinish odatda yana timeout — modelni almashtiramiz
                except Exception as e:
                    last_error = f"{m_id}: {type(e).__name__}: {e}"
                    attempts.append({"model": m_id, "error": last_error})
                    break

                duration_ms = round((time.time() - t0) * 1000)

                if result["ok"]:
                    parsed = result["parsed"]
                    usage = result["usage"]
                    models_hub.record_usage(
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                        usage.get("reasoning_tokens", 0),
                    )
                    models_hub.note_live_success(m_id, duration_ms)

                    out = {
                        "success": True,
                        "text": parsed["text"],
                        "reasoning": parsed["reasoning"],
                        "tool_calls": parsed["tool_calls"],
                        "finish_reason": parsed.get("finish_reason", ""),
                        "usage": usage,
                        "model_used": m_id,
                        "provider": provider_id,
                        "duration_ms": duration_ms,
                        "cached": False,
                        "fallback_used": m_id != model_id,
                        "attempts": attempts,
                    }
                    if cacheable:
                        prompt_cache.set(
                            model_id, messages,
                            {"text": parsed["text"], "reasoning": parsed.get("reasoning", ""), "tool_calls": parsed.get("tool_calls", [])},
                            tokens_saved=max(120, usage.get("prompt_tokens", 0))
                        )
                    return out

                status = result["status"]
                last_error = f"{m_id}: HTTP {status} — {result.get('detail', '')[:160]}"
                retry_after = result.get("retry_after")
                attempts.append({"model": m_id, "status": status, "retry_after": retry_after})
                models_hub.note_live_failure(m_id, status, retry_after=retry_after)

                # 429 va 5xx — vaqtinchalik; Retry-After yoki eksponensial backoff.
                if status in (429, 500, 502, 503, 504, 529) and attempt < retries:
                    if retry_after and retry_after > 0:
                        backoff = min(float(retry_after), 12.0)
                    else:
                        backoff = min(8.0, (2 ** attempt) * 1.2) + random.uniform(0, 0.6)
                    await asyncio.sleep(backoff)
                    continue
                break  # 4xx (auth, noto'g'ri model) — qayta urinish befoyda

        return {
            "success": False,
            "error": f"Ошибка подключения ко всем моделям: {last_error}",
            "text": "", "reasoning": "", "tool_calls": [],
            "usage": {}, "model_used": model_id, "provider": "",
            "duration_ms": 0, "cached": False, "fallback_used": True,
            "attempts": attempts,
        }

    async def _call_provider(
        self, provider_id: str, model_id: str,
        messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]],
        temperature: float, max_tokens: int, timeout_s: float,
        custom_keys: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        provider = dict(PROVIDERS.get(provider_id, PROVIDERS["gemini"]))
        api_key = models_hub.get_api_key(provider_id, custom_keys)

        # BYOK ulanishi o'z base URL'ini bergan bo'lsa (Custom OpenAI-compatible,
        # Ollama yoki self-hosted gateway), u registry qiymatidan ustun turadi.
        byok_base = models_hub.byok_base_url(provider_id)
        if byok_base:
            provider["base_url"] = byok_base
        timeout = aiohttp.ClientTimeout(total=timeout_s, sock_connect=8,
                                        sock_read=max(30.0, timeout_s * 0.85))

        async with aiohttp.ClientSession(timeout=timeout) as session:
            if provider_id == "gemini":
                contents, system_text = _to_gemini_payload(messages)
                payload: Dict[str, Any] = {
                    "contents": contents,
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
                }
                if system_text:
                    payload["systemInstruction"] = {"parts": [{"text": system_text}]}
                if tools:
                    payload["tools"] = [{"functionDeclarations": tools}]

                url = (f"{provider['base_url']}/models/{model_id}:generateContent"
                       f"?key={api_key}")
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        return {"ok": False, "status": resp.status,
                                "detail": await resp.text(),
                                "retry_after": _parse_retry_after(resp.headers)}
                    res_json = await resp.json()

                parsed = _parse_gemini_response(res_json)
                um = res_json.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": um.get("promptTokenCount", 0),
                    "completion_tokens": um.get("candidatesTokenCount", 0),
                    "reasoning_tokens": um.get("thoughtsTokenCount", 0),
                }
                return {"ok": True, "parsed": parsed, "usage": usage}

            # OpenAI-mos provayderlar (17.wtf, OpenRouter, Groq, GitHub)
            url = f"{provider['base_url']}{provider.get('chat_endpoint', '/chat/completions')}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) AntColonyAI/1.0"
            }
            payload = {
                "model": model_id,
                "messages": _to_openai_messages(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = [{"type": "function", "function": t} for t in tools]
                payload["tool_choice"] = "auto"
            if _model_meta(model_id).get("supports_reasoning") and provider_id == "openrouter":
                payload["reasoning"] = {"enabled": True}

            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    return {"ok": False, "status": resp.status,
                            "detail": await resp.text(),
                            "retry_after": _parse_retry_after(resp.headers)}
                res_json = await resp.json()

            if not res_json.get("choices"):
                return {"ok": False, "status": 502,
                        "detail": f"Javobda `choices` yo'q: {str(res_json)[:200]}"}

            parsed = _parse_openai_response(res_json)
            raw_usage = res_json.get("usage", {}) or {}
            usage = {
                "prompt_tokens": raw_usage.get("prompt_tokens", 0),
                "completion_tokens": raw_usage.get("completion_tokens", 0),
                "reasoning_tokens": (raw_usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                "total_tokens": raw_usage.get("total_tokens", 0),
            }
            return {"ok": True, "parsed": parsed, "usage": usage}


llm_client = LLMClient()
