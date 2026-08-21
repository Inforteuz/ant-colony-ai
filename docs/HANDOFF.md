# Handoff — Ant Colony AI (session history & open work)

_Purpose: let the next session (Claude Code) pick this project up without re-discovering context.
Companion to root `CLAUDE.md`. Last updated 2026-08-21._

---

## 1. Status snapshot

| Area | State | Commit |
|---|---|---|
| Multi-language UI (uz/ru/en + kirill) | ✅ complete | `155c1c8` |
| PM panel + Live Workspace localisation (root-cause fix) | ✅ complete | `bc5d1c0` |
| 3D canvas role/action labels localised | ✅ complete | `155c1c8` |
| Language switcher (custom dropdown) | ✅ complete | `155c1c8` |
| 17.wtf provider — backend (config/registry/client/server) | ✅ complete | `d4afad8` |
| 17.wtf provider — Setup Wizard UI | ✅ complete | `f4327c7` |
| LLM reply follows UI language | ✅ wired (verified) | `bc5d1c0` |

---

## 2. What was done (narrative)

### Session A — Multi-language scaffolding
- Built `static/js/i18n.js`: a custom sweeper (`window.I18N` with `t`, `translateText`,
  `applyLanguage`, `getCurrentLang`, `setLang`). `applyLanguage` walks `data-i18n*`
  attributes, then `sweepTextNodes` (TreeWalker + token-level fallback for dynamic strings)
  and `sweepAttributes` (title/placeholder/aria-label). A `MutationObserver` re-sweeps on DOM
  mutations.
- `STRINGS` holds en/uz/ru; `uz_cyr` is auto-generated from uz via `uzToCyr`. An `EXTRA` block
  (IIFE) merges project-specific keys into all three dicts.
- `index.html`: replaced the native `<select id="lang-select">` with a custom nav-button
  dropdown (`#lang-btn` + `#lang-dropdown-menu`) reusing the Tools ▾ portal pattern.
- `app.js`: `drawStation()` localises the 3D station role labels via
  `I18N.t(roleKey, lang)`; canvas action badges via `localizeCanvasAction()` +
  `CANVAS_ACTION_MAP`.
- Commit `155c1c8` ("feat: Ko'p tilli interfeys …").

### Session B — 17.wtf provider review (#task: add 17.wtf via Settings)
- Backend verified **100% complete & compiles**:
  - `ant_colony/config.py`: `PROVIDERS["17_wtf"]` (base_url `https://api.17.wtf/v1`,
    default key `WTF_API_KEY`, `/chat/completions`) + 5 models in `MODELS_CATALOG`.
  - `ant_colony/providers/registry.py`: `PROVIDER_DEFINITIONS["17_wtf"]`
    (`DRIVER_OPENAI_CHAT`, `AUTH_BEARER`) and it is in `PROVIDER_ORDER`.
  - `ant_colony/llm/client.py`: `_provider_for()` resolves catalog model_id → provider.
  - `ant_colony/server.py`: `SetupConfigRequest.wtf_key`; `save_setup_configuration` sets
    `CUSTOM_KEYS["17_wtf"]` and merges `WTF_API_KEY` into `.env`; `test_connection`
    `17_wtf` → `https://api.17.wtf/api/v1/models`.
- **Frontend gap found:** the Setup Wizard single `<select>` only offers
  github/openrouter/gemini/openai/groq (no `17_wtf`); the multi-inputs offer the same 4
  (no 17.wtf); `app.js` save handler sends github/openrouter/gemini/openai/groq keys only —
  it **never sends `wtf_key`**. So users must edit `.env` (`WTF_API_KEY=…`) by hand.
  → This is the single remaining action item; see §4.

### Session C — PM panel root-cause fix (the screenshot complaint)
The user reported the PM chat panel stayed in Russian after switching languages. Root cause
had **two parts**:
1. **Static UI chrome not localising.** `#pm-feed-list` had `data-i18n-skip`, which skipped the
   whole container — including the empty-state placeholder (`pm_idle_title`/`pm_idle_body`).
   Fix: removed the container skip and instead skip only **dynamic feed items** by class in
   `shouldSkip` (`.pm-feed-item`, `.chat-thinking-card`, `.exec-summary-card`). So the
   empty-state UI chrome translates, but agent conversation never does.
2. **Hardcoded-Russian greeting.** `app.js` `showPmGreeting()` built the idle CEO greeting from
   hardcoded Russian strings — duplicating keys that already exist as `ceo_greeting_*`. Rewrote
   it to use `I18N.t('ceo_greeting_*', params)` (current UI lang); marked the greeting card
   `data-i18n-skip` so the sweeper never corrupts it.

Also localised the **Live Workspace drawer** (subtitle, live label, refresh/clear/close
buttons) using existing `lw_*` keys, and the PM input area (path placeholder/apply, drop hint,
input hint, stop/send). The regenerated empty-placeholder markup in `clearChatHistory` and the
`cancelled` branch got `data-i18n` so it translates on re-render too.

The screenshot's body text "Остаюсь за пультом…" is an **LLM-generated reply** (not in code).
Verified the backend already steers agent replies to the UI language
(`resolve_response_language` honours an explicit UI language; frontend dispatch omits
`language` but the backend falls back to `get_language_preference()`). No backend change needed.

- Verified: `node --check` on `app.js`/`i18n.js` OK; 17/17 PM-key resolution checks passed.
- Commit `bc5d1c0` ("fix(i18n): PM panel va Live Workspace UI matnlarini to'liq tarjima qilish").

---

## 3. Architecture notes that matter for continuation

- **No frontend build.** Edits to `static/` are live after a hard-reload. Backend changes need
  `run.py` restart.
- **i18n is attribute-driven**, not component-driven. To add a translatable string: put the key
  in all 3 dicts in `i18n.js`, then mark the element with `data-i18n*`. For JS-built strings
  (toasts, dynamic cards) call `I18N.t(key, …)` directly.
- **Never auto-translate agent output.** Any element holding an LLM response must carry
  `data-i18n-skip` or one of the feed-item classes, or the sweeper will mangle it.
- **Language persistence:** `setLang` POSTs to `/api/settings/language`; backend stores it and
  `get_language_preference()` returns it. The frontend does not send `language` on dispatch, by
  design — the backend resolves it.
- **Provider model IDs are never hardcoded**; they are synced from each provider's `/models`
  endpoint. `17.wtf` models live in `MODELS_CATALOG` as a seed.

---

## 4. Open task queue (do these next)

### T1 — Wire 17.wtf into the Setup Wizard UI  ⭐ top priority  ✅ DONE (commit `f4327c7`)
Backend was ready; the frontend is now wired too.
- `static/index.html`: added `<option value="17_wtf">17.wtf</option>` to the provider `<select>`
  in the single-provider wizard.
- `static/index.html`: added a `setup-multi-wtf` text input (mirrors the existing multi-key inputs)
  plus a "Проверить" button (`data-test-provider="17_wtf"`) and `key-test-17_wtf` result div.
- `static/js/app.js`: the Setup Wizard save handler now sends `wtf_key` in **both** the single
  branch (`else if (prov === '17_wtf') payload.wtf_key = key;`) and the multi branch
  (`payload.wtf_key = document.getElementById('setup-multi-wtf').value.trim();`).
- Verified: `node --check` passes; backend `server.py` already writes `WTF_API_KEY` to `.env` and
  `test-key` resolves `17_wtf` → `https://api.17.wtf/api/v1/models`. 17.wtf is end-to-end usable
  without editing `.env`.

### T2 — (optional) localise transient toasts
A few `this.toast(...)` / `pmFeedError(...)` calls in `app.js` still pass hardcoded Russian
(e.g. the orchestrator error toast). Wrap them in `I18N.t(...)`. Lower priority — they are
ephemeral and the static chrome is already covered.

### T3 — Browser smoke-test of language switching
Confirm in a real browser: switch to O'zbek → PM console, Live Workspace, chips, canvas labels,
and an actual LLM reply all appear in Uzbek. The static/greeting paths are unit-verified; the
live LLM-reply path is wired but only verified by reading the backend.

---

## 5. How to verify a change
- JS syntax: `node --check static/js/app.js && node --check static/js/i18n.js`
  (use the managed Node at `C:/Users/Oybek/.workbuddy/binaries/node/versions/22.22.2/node.exe`
  if the system one is missing).
- Backend import/boot: `python -c "import ant_colony.server"` from the venv.
- i18n key resolution: a Node `vm` harness that stubs `document`/`window` and calls
  `I18N.t(key, lang)` — reuse the pattern from the workspace `_pmcheck.js` if needed.
- Always hard-reload the browser (cache-bust) after static edits.
