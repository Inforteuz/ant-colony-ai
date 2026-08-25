# Status Notes

Last updated: 2026-08-19

## Provider integrations (BYOK)

All providers use the OpenAI-compatible Chat Completions contract at runtime
(`ant_colony/llm/client.py`), except Gemini (native Interactions API).

| Provider    | Env key              | Free models | Notes |
|-------------|----------------------|-------------|-------|
| gemini      | `GEMINI_API_KEY`     | Yes         | Native Gemini Interactions API. |
| openrouter  | `OPENROUTER_API_KEY` | Yes (many)  | Multi-provider aggregator. |
| groq        | `GROQ_API_KEY`       | Yes         | Ultra-fast LPU. |

| b_ai        | `BAI_API_KEY`        | No          | **Asosiy tanlov.** OpenAI-mos, 42 model (claude-*, gpt-5.*, gemini-3.*, deepseek-v4-*, hy3, qwen3.8-*). 17.wtf dagi bir xil modellardan sezilarli tez. |
| 17_wtf      | `WTF_API_KEY`        | Yes (posiden/*, elon/grok-4.5-free) | ⚠️ Hisobda token tugagan — ko'p modellar HTTP 402. |
| github      | `GITHUB_TOKEN`       | —           | ❌ **YOPILGAN** (`github_models_retirement_brownout`). `retired: True`, tanlovga tushmaydi. |
| openai      | `OPENAI_API_KEY`     | No          | Wired for direct paid use. |
| custom      | `CUSTOM_BASE_URL` / `CUSTOM_API_KEY` | n/a | Ollama / LM Studio / vLLM. |

## Two registries (keep in sync)

1. `ant_colony/config.py` — `PROVIDERS` + `MODELS_CATALOG` (runtime path).
2. `ant_colony/providers/registry.py` — `PROVIDER_DEFINITIONS` + `PROVIDER_ORDER` (UI path).

When adding a provider, populate **both** or it will be partially broken.

## Known issues (resolved)

- `cryptography` was missing from `requirements.txt` — added.
- `scripts/install.py` wrote wrong env names (`PORT`/`HOST`) and nuked `.env`;
  fixed to write `ANT_HOST`/`ANT_PORT` and merge instead of overwrite.
- `.env` no longer carries ignored `SETUP_MODE` / `PRIMARY_PROVIDER` vars.

## Security note

Do **not** bind `ANT_HOST=0.0.0.0` on an untrusted network — the platform
exposes a shell-executing endpoint with no auth (authenticated RCE risk).


## Provayder holati — 2026-08-25 o'lchovi

Diagnostika `venv` dan haqiqiy so'rov bilan bajarildi (taxmin emas):

| Provayder | Natija | Izoh |
|---|---|---|
| b.ai `hy3` | **2 170 ms** | asosiy tanlov |
| 17.wtf `hy3` | 17 015 ms | 7.8× sekin |
| b.ai `deepseek-v4-flash` | **1 350 ms** | |
| 17.wtf `deepseek-v4-flash` | HTTP 402 | `insufficient tokens` |
| github (barcha endpoint) | HTTP 410 / DNS yo'q | xizmat yopilgan |
| openai | kalit yo'q | 7 model o'lik |

**Xulosa:** katalogdagi 30 modeldan 16 tasi o'lik edi va har chaqiruv ular
bo'ylab zaxira zanjirida urinardi — "performance tushib ketdi" ning sababi shu.

Diagnostikani qayta yugurtirish uchun `.env` kalitlari bilan har provayderning
`/models` endpointiga GET yuborish yetarli; kalitni **hech qachon** taxmin
qilingan hostga yubormang.

### Yangi provayder qo'shganda
1. `config.py` — `PROVIDERS` + `MODELS_CATALOG` (runtime yo'li)
2. `providers/registry.py` — `PROVIDER_DEFINITIONS` + `PROVIDER_ORDER` (UI yo'li)
3. `server.py` — `test_connection` shoxi + `SetupConfigRequest.<x>_key` +
   `CUSTOM_KEYS` + `managed` env
4. `static/index.html` — single `<option>` **va** multi input.
   Multi input id **majburan** `setup-multi-<provider_id>` bo'lsin:
   `testProviderKey(scope)` uni `setup-multi-${scope}` bo'yicha qidiradi.
   17.wtf da bu qoida buzilgani uchun "Проверить" tugmasi umuman ishlamagan.
5. `static/js/app.js` — save handler'ning **ikkala** shoxi
6. `.env.example`
