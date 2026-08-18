# Ant Colony AI

**An autonomous multi-agent platform with a live 3D office.** You give one task to the
Project Manager agent; it plans the architecture, splits the work across specialised AI
agents (developer, designer, QA, DevOps, analyst, marketer, legal), runs them against real
tools, and writes a finished project to your workspace — while you watch the agents walk
around a 3D office and work at their desks.

> ⚠️ **Security first:** this platform executes shell commands and writes files on the
> machine it runs on. Read [Security model](#security-model) before exposing it to a network.

---

## Highlights

| | |
|---|---|
| **Multi-agent orchestration** | A PM agent decomposes a task, assigns roles, runs a QA + repair loop, and reports back to you (the "CEO"). If no existing role fits, it writes a new one into `roles/` and uses it. |
| **BYOK — bring your own key** | Connect OpenAI, Anthropic, Gemini, Groq, OpenRouter, Mistral, DeepSeek, xAI, Cerebras, Cohere, Together AI, Ollama, or any OpenAI-compatible endpoint. Keys are encrypted at rest and never returned to the browser. |
| **Work on your own files** | Drop a file, a ZIP archive, or point at a folder — agents unpack it, read it, edit in place, and hand back the same shape (ZIP in → ZIP out). |
| **One fallback chain** | All connected providers sit behind a single routing layer with circuit breakers, provider-diverse fallback, and normalized errors. Configuration mistakes never trigger a pointless retry storm. |
| **Continuous ELO matrix** | Every finished task scores the model that did it. Roles get reassigned to whichever model actually performs best per category. |
| **Prompt cache** | Repeated prompts are served from disk, with per-model savings reporting. |
| **Live 3D office** | Three.js scene: workstations, walking agents, meeting room, marketing/BI wing, legal office, and recreation areas. |
| **Real tools** | File read/write/edit, directory walking, sandboxed shell execution, Python execution, project scaffolding. |
| **Telegram control** | Optionally drive the whole pipeline from a Telegram bot. |

---

## Quick start

**Requirements:** Python 3.10+ and at least one LLM provider API key.

```bash
git clone <your-fork-url> ant-colony-ai
cd ant-colony-ai

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then put at least one API key in .env
python run.py
```

Open <http://127.0.0.1:8080>.

No keys yet? Any one of these is enough to start:

| Provider | Free tier | Get a key |
|---|---|---|
| Google Gemini | yes | <https://aistudio.google.com/apikey> |
| OpenRouter | yes (`:free` models) | <https://openrouter.ai/keys> |
| Groq | yes | <https://console.groq.com/keys> |
| GitHub Models | yes | <https://github.com/settings/tokens> |

You can also add keys from the UI (**Настройки → Setup Wizard**); they are written to `.env`
and reloaded on the next start.

---

## Connecting a provider (BYOK)

Open **Настройки → Мои провайдеры (BYOK)**, pick a provider, paste your key and press
**Проверить**. On success the platform loads that provider's live model list and saves the
credential.

What happens to your key:

- it is sent **only** to your own backend, never to a third party;
- it is stored with **AES-256-GCM** envelope encryption in `data/provider_connections.json` (mode `0600`);
- the encryption key lives outside that file — `ANT_SECRET_KEY`, `ANT_SECRET_KEY_FILE`,
  or an auto-generated `~/.ant_colony/secret.key`;
- it is written to disk **only after** a successful connection test;
- read endpoints return a masked fingerprint (`sk-...ABCD`) and never the raw value;
- provider error bodies are never forwarded to the browser.

For a server deployment, generate a key first:

```bash
python -c "from ant_colony.providers.secrets import generate_master_key; print(generate_master_key())"
# put the output in ANT_SECRET_KEY
```

Custom endpoints (vLLM, LM Studio, a gateway) go through the **Custom (OpenAI-compatible)**
entry. Because you supply the URL there, it is validated against SSRF: only `http(s)`, no
credentials-in-URL, and private / loopback / link-local / cloud-metadata addresses are
rejected. Local addresses are allowed only for Ollama, which is explicitly a local provider.

Model IDs are never hardcoded — they are synced from each provider's models endpoint, and a
model that disappears is marked unavailable rather than deleted, so historical agent runs
stay readable.

## Working with your own files

The PM console accepts three kinds of input alongside the task text:

| Input | What happens | What you get back |
|---|---|---|
| A file | Placed in a scratch workspace | The edited file |
| A ZIP archive | Unpacked (Zip Slip and zip-bomb guarded) | A new ZIP with the changes |
| A folder path | Used in place, no copying | Edits applied on disk |

The PM sees the file tree and the contents of the text files before planning, so it works
from what you actually sent rather than from a guess. Paths are restricted to your projects
directory and home directory.

## Configuration

Everything is environment-driven — see [`.env.example`](.env.example) for the full list.

| Variable | Default | Meaning |
|---|---|---|
| `ANT_HOST` | `127.0.0.1` | Bind address. **Do not** change without reading [Security model](#security-model). |
| `ANT_PORT` | `8080` | HTTP port. |
| `ANT_RELOAD` | `0` | Auto-reload for development. |
| `PROJECTS_BASE_DIR` | `~/AntColonyProjects` | Where agents create their projects. |
| `AGENT_MAX_TOOL_STEPS` | `8` | Max sequential tool calls per agent run. |
| `AGENT_REPAIR_THRESHOLD` | `80` | QA score below which the repair loop triggers. |
| `ANT_SECRET_KEY` | auto-generated locally | base64 AES-256 key used to encrypt provider credentials. Set this on a server. |
| `ANT_SECRET_KEY_FILE` | — | Path to a file holding that key instead. |
| `TELEGRAM_BOT_TOKEN` | — | Enables the Telegram control bot. |

Keys are read **only** from the environment (`.env` or system env). Nothing is hardcoded.

---

## Security model

This is a local-first developer tool, not a hardened multi-tenant service. Understand
these three facts before deploying it anywhere shared:

1. **There is no authentication.** Every HTTP endpoint is open to whoever can reach the port.
2. **`POST /api/terminal/exec` runs shell commands** in the workspace directory. There is a
   blocklist of destructive patterns and Unix resource limits (CPU, file size, process
   count), but a blocklist is not a sandbox.
3. **Agents write files** to `PROJECTS_BASE_DIR` and can execute the code they write.

Consequently:

- The server binds to `127.0.0.1` by default. Setting `ANT_HOST=0.0.0.0` exposes remote
  code execution to everyone on that network. Only do it inside an isolated network or
  behind an authenticating reverse proxy.
- Prefer running it in a container or VM if you plan to leave it up.
- Never point `PROJECTS_BASE_DIR` at a directory containing data you cannot afford to lose.

Found a security issue? Please open a private report rather than a public issue.

---

## Architecture

```
                    ┌──────────────────────────────┐
   Browser  ◄──SSE──┤  server.py  (FastAPI)        │
   (3D UI)          └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  agent_engine / agent_loop   │  plan → delegate → QA → repair
                    └──────────────┬───────────────┘
                                   │
        ┌──────────────┬───────────┴────────┬──────────────────┐
        ▼              ▼                    ▼                  ▼
   llm_client     skill_matrix         prompt_cache          tools
  (providers,     (ELO scoring,        (disk cache,      (fs, shell, python,
   fallback,       role→model           per-model          resource limits)
   circuit         assignment)          savings)
   breaker)
```

```
run.py                        # entrypoint — python run.py
ant_colony/
├── config.py                 # paths, provider registry, agent tuning
├── server.py                 # HTTP + SSE API, static hosting
├── core/                     # orchestration
│   ├── agent_engine.py       # agent run loop
│   ├── agent_loop.py         # tool-call parsing, repair cycle
│   ├── skill_matrix.py       # continuous ELO, role→model assignment
│   ├── pm_memory.py          # long-term PM memory
│   └── pm_proactive.py       # proactive CEO briefings
├── llm/
│   ├── client.py             # fallback chain, retries, timeouts
│   ├── models_hub.py         # health, latency, tokens, circuit breakers
│   └── prompt_cache.py       # disk cache + savings stats
├── providers/                # BYOK: registry, drivers, secrets, SSRF guard
│   └── drivers/              # one driver per wire protocol
├── runtime/
│   ├── tools.py              # fs / shell / python tools + safety layer
│   └── workspace_janitor.py
└── integrations/
    └── telegram_bot.py
static/                       # web UI (index.html, css/, js/, vendor/)
roles/                        # editable system prompts, one .md per role
data/                         # runtime state — gitignored
docs/                         # specs and status notes
scripts/                      # install.py, setup.sh
tests/
```

---

## Adding a role

Roles are plain Markdown. Drop a file into `roles/`, e.g. `roles/data_scientist.md`:

```markdown
# Data Scientist

## Role description
Builds analysis notebooks and statistical models.

## Key skills
- Exploratory data analysis
- Feature engineering
- Model evaluation and reporting
```

Register it in `DEFAULT_ROLE_DEFINITIONS` in `ant_colony/config.py` with an `initial_model`, and the
role appears in the UI, gets ELO-scored, and becomes assignable by the PM. You can also
create and edit roles live from **Инструменты → Редактор навыков**.

## Adding a provider

Add an entry to `PROVIDERS` in `ant_colony/config.py` (base URL, key env var, chat endpoint) and list
its models in `MODELS_CATALOG`. OpenAI-compatible endpoints work without new adapter code;
anything else needs a driver in `ant_colony/providers/drivers/`.

---

## Contributing

Issues and pull requests are welcome. Please:

- keep the existing code style (comments explain *why*, not *what*);
- verify the UI in both light and dark themes;
- never commit secrets, `.env`, or anything under `data/`.

## License

[MIT](LICENSE).

---

## Tez boshlash (o'zbekcha)

**Talab:** Python 3.10+ va kamida bitta LLM provayder kaliti.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # .env ichiga kamida bitta API kalit yozing
python run.py          # http://127.0.0.1:8080
```

Kalitni UI orqali ham kiritish mumkin: **Настройки → Setup Wizard**. Kalitlar `.env` ga
yoziladi va keyingi ishga tushirishda avtomatik o'qiladi.

**Xavfsizlik:** platforma shell buyruqlarini bajaradi va fayl yozadi, autentifikatsiya
yo'q. Shu sababli server standart holatda faqat `127.0.0.1` da tinglaydi. `ANT_HOST=0.0.0.0`
qilish — tarmoqdagi har kimga masofadan buyruq bajarish imkonini berish demakdir; buni
faqat izolyatsiyalangan tarmoqda yoki autentifikatsiyalovchi proksi ortida qiling.
