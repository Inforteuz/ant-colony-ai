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
| github      | `GITHUB_TOKEN`       | Yes         | GitHub Models. |
| 17_wtf      | `WTF_API_KEY`        | Yes (posiden/*, elon/grok-4.5-free) | User-added free provider. |
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
