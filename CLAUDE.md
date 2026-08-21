# CLAUDE.md — Ant Colony AI

> Context file for Claude Code. Read this first, then `docs/HANDOFF.md` for the full session
> history and the open task queue.

## What this is
An autonomous multi-agent platform with a live 3D office. The user (the "CEO") gives one
task to a **Project Manager** agent; it plans, splits work across specialised AI agents
(developer, designer, QA, DevOps, analyst, marketer, legal), runs them against real tools,
and writes a finished project to disk — streamed live to a Three.js UI at
`http://127.0.0.1:8080`.

## Run it
```bash
cd ant-colony-ai
venv\Scripts\activate            # Windows (venv already created, Python 3.13)
python run.py                    # → http://127.0.0.1:8080  (FastAPI, SSE)
```
- At least one LLM key must be in `.env` (`cp .env.example .env` first). For a server, set
  `ANT_SECRET_KEY` (see README "Security model").
- Frontend is static (`static/index.html`, `static/js/*.js`, `static/css/*.css`) — no build
  step. Hard-reload after edits. Backend is `ant_colony/` (package); entrypoint `run.py`.

## Current state (as of 2026-08-21)
- **Multi-language UI: DONE.** uz / ru / en (+ `uz_cyr` auto-generated from uz). All static
  chrome localised; PM panel + Live Workspace drawer fixed at root cause (commit `bc5d1c0`).
- **17.wtf provider: DONE end-to-end.** Backend (`server.py` saves `WTF_API_KEY` into `.env`
  and `test-key` hits `https://api.17.wtf/api/v1/models`) and frontend (Setup Wizard single +
  multi panels offer 17.wtf, save handler sends `wtf_key`). Commit `f4327c7`; the multi-input
  id was later renamed to `setup-multi-17_wtf` so the "Проверить" button finds it
  (`testProviderKey` looks up `setup-multi-${scope}` where scope is the provider id).
- **PM feed clear is now durable.** `POST /api/orchestrator/forget` cancels any running job
  *and* drops the server-side job history, so a reload no longer replays a cleared chat.
- **CEO "Активный агент и модель" syncs live** from `reasoning` / `agent_message` /
  `model_fallback` events (they carry the *actual* model), not just the coarse
  `ceo_briefing` checkpoints.
- **LLM reply language: wired correctly.** Backend steers the PM/agent reply to the selected
  UI language; frontend `/api/orchestrator/dispatch` does NOT send `language` and the backend
  falls back to the saved preference (`get_language_preference()`).

## The i18n system (READ BEFORE any UI/text change)
Everything lives in `static/js/i18n.js`. There is **no framework** — a custom sweeper runs on
`document` and on a `MutationObserver`.

- `window.I18N.t(key, langOrParams)` — `t(key)` uses current UI lang; `t(key, 'uz')` forces a
  lang; `t(key, {n: 3})` does `{n}` substitution. `I18N.getCurrentLang()` returns the active lang.
- Add a key in **all three** dicts in `i18n.js` (en / uz / ru blocks — there is an `EXTRA`
  IIFE near the bottom that merges keys; new keys usually go there or in the main `STRINGS`).
- Mark an element with `data-i18n="key"` (text), `data-i18n-placeholder="key"`,
  `data-i18n-title="key"`, or `data-i18n-task="key"` (sets the element's `data-task` attribute —
  used by the suggestion chips).
- **Skip rules** (in `shouldSkip`): elements with `data-i18n-skip`, or with class
  `.pm-feed-item` / `.chat-thinking-card` / `.exec-summary-card` (these are LLM responses and
  must NEVER be auto-translated). `#lang-btn` / `#lang-dropdown-menu` are also skipped.
  → If you add dynamic agent output, give it one of those classes so the sweeper leaves it alone.
- **3D canvas labels** are NOT DOM — `static/js/app.js` `drawStation()` calls
  `I18N.t(roleKey, I18N.getCurrentLang())` directly. Canvas action badges go through
  `localizeCanvasAction()`.

## Key files
| File | Role |
|---|---|
| `ant_colony/config.py` | `SUPPORTED_LANGUAGES`, `get_language_preference()`, `PROVIDERS`, `MODELS_CATALOG`, `DEFAULT_ROLE_DEFINITIONS` |
| `ant_colony/server.py` | FastAPI routes: `/api/settings/language`, `/api/orchestrator/dispatch`, `/api/pm/*`, Setup Wizard save |
| `ant_colony/core/agent_engine.py` | `_plan_with_pm` (PM prompt + language rule), `resolve_response_language`, `_orchestrate` |
| `ant_colony/providers/registry.py` | `PROVIDER_DEFINITIONS`, `PROVIDER_ORDER` |
| `static/js/i18n.js` | the sweeper + all translation strings |
| `static/js/app.js` | frontend controller (PM console, canvas, dispatch, greeting) |
| `static/index.html` | PM console drawer + Live Workspace drawer markup |
| `roles/*.md` | one editable system prompt per agent role |

## Open tasks (continue here)
1. ~~Wire 17.wtf into the Setup Wizard UI~~ ✅ DONE (commit `f4327c7`): both single + multi
   wizard panels offer 17.wtf and the save handler sends `wtf_key`; no remaining open tasks
   from this session.
2. (Optional) Localise the remaining hardcoded-Russian **toast/error** strings in `app.js`
   via `I18N.t` — lower priority, they are transient.
3. Smoke-test language switching in a real browser (the static chrome + greeting are covered;
   verify an actual LLM reply follows the UI language).

## Conventions
- Comments explain *why*, not *what* (repo style).
- Commit messages so far are Conventional Commits, sometimes mixed Uzbek (e.g.
  `fix(i18n): PM panel va Live Workspace UI matnlarini to'liq tarjima qilish`).
- Never commit `.env`, `data/`, or `venv/`.
