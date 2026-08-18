"""
FastAPI Server for Ant Colony AI Platform: Central PM Orchestrator, Desktop Projects (04_Loyihalar), Terminal Runner, Prompt Cache, and CEO Executive Briefing.
"""
import os
import re
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    BASE_DIR, WORKSPACE_DIR, PROJECTS_BASE_DIR, PROVIDERS, MODELS_CATALOG,
    WORKSTATIONS, AGENT_CONFIG,
)
from models_hub import models_hub
from agent_engine import agent_engine
from skill_matrix import skill_matrix
from prompt_cache import prompt_cache
from workspace_janitor import WorkspaceJanitor
from pm_memory import PMMemory, init_memory, get_memory
from tools import (
    AVAILABLE_TOOLS, get_tool_schemas, list_files, read_file, run_shell_command,
    get_active_project_dir, set_active_project_dir, AGENT_MEMORY, set_event_emitter,
    walk_project_files, _skip_entry, MAX_WALK_FILES,
)
import config as _config_module

app = FastAPI(title="Ant Colony AI Agent Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    # Start continuous background health monitor for all models
    models_hub.start_background_monitor()
    # Bo'sh loyiha papkalarini tozalovchi fon vazifasi
    global _JANITOR
    _JANITOR = WorkspaceJanitor(
        projects_base_dir_getter=lambda: _config_module.PROJECTS_BASE_DIR,
        log_path=BASE_DIR / "janitor_log.jsonl",
        is_orchestration_active_getter=lambda: (CURRENT_JOB is not None and CURRENT_JOB.status == "running"),
    )
    _JANITOR.start()
    # PM Memory — long-term xotira (fayl asosida)
    init_memory(BASE_DIR / "pm_memory.json")


_JANITOR: Optional[WorkspaceJanitor] = None

# In-memory storage
AGENTS_STORE: Dict[str, Dict[str, Any]] = {a["id"]: a.copy() for a in WORKSTATIONS.values()}

CUSTOM_KEYS: Dict[str, str] = {
    "gemini": PROVIDERS["gemini"]["default_key"],
    "17_wtf": PROVIDERS["17_wtf"]["default_key"],
    "openrouter": PROVIDERS["openrouter"]["default_key"]
}

# --- Roles & Skill Matrix Endpoints ---

@app.get("/api/roles")
async def get_roles():
    return {
        "roles": skill_matrix.get_all_roles(),
        "leaderboard": skill_matrix.get_leaderboard()
    }

@app.get("/api/roles/{role_id}/md")
async def get_role_md(role_id: str):
    roles = skill_matrix.get_all_roles()
    target = next((r for r in roles if r["id"] == role_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Rol topilmadi")
    content = skill_matrix.get_role_md_content(target["md_file"])
    return {"role": target, "md_content": content}

# --- Skill & MD Editor Endpoints ---

class EditorSaveRequest(BaseModel):
    content: str

class CreateSkillRequest(BaseModel):
    role_id: str
    name: str
    category: str = 'general'
    description: str = ''
    content: str = ''

class CreateMdRequest(BaseModel):
    filename: str
    content: str = ''

class FetchModelsRequest(BaseModel):
    base_url: str
    api_key: Optional[str] = ''

class ImportCustomModelsRequest(BaseModel):
    base_url: str
    api_key: Optional[str] = ''
    models: List[Dict[str, Any]]

@app.get("/api/skills")
async def list_skill_files():
    """Skill MD fayllar ro'yxatini qaytaradi."""
    skills_dir = BASE_DIR / "roles"
    files = []
    if skills_dir.exists():
        files = sorted([f.name for f in skills_dir.iterdir() if f.suffix == ".md" and not f.name.startswith(".")])
    return {"files": files, "dir": str(skills_dir)}

@app.post("/api/skills/create")
async def create_skill_file(req: CreateSkillRequest):
    """Yangi Skill yoki Rol yaratadi."""
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '_', req.role_id.strip().lower())
    if not clean_id:
        clean_id = f"custom_role_{int(time.time())}"
    fname = f"{clean_id}.md"
    skill_path = BASE_DIR / "roles" / fname
    default_content = req.content.strip() or f"# {req.name}\n\n## Описание роли\n{req.description}\n\n## Ключевые навыки (Skills)\n- Экспертное выполнение задач\n"
    skill_path.write_text(default_content, encoding="utf-8")

    # Register in skill matrix engine
    skill_matrix.register_custom_role({
        "id": clean_id,
        "name": req.name.strip() or clean_id,
        "category": req.category or "general",
        "icon": "star",
        "description": req.description.strip() or req.name,
        "md_file": fname,
        "initial_model": "posiden/deepseek-v4-flash"
    })
    return {"success": True, "role_id": clean_id, "filename": fname}

@app.get("/api/skills/{filename}")
async def get_skill_file(filename: str):
    """Skill MD faylini o'qiydi."""
    safe_name = os.path.basename(filename.strip())
    if not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="Разрешены только .md файлы")
    skill_path = BASE_DIR / "roles" / safe_name
    if not skill_path.exists():
        raise HTTPException(status_code=404, detail=f"Файл не найден: {safe_name}")
    content = skill_path.read_text(encoding="utf-8")
    return {"filename": safe_name, "content": content}

@app.post("/api/skills/{filename}")
async def save_skill_file(filename: str, req: EditorSaveRequest):
    """Skill MD faylini saqlaydi."""
    safe_name = os.path.basename(filename.strip())
    if not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="Разрешены только .md файлы")
    skill_path = BASE_DIR / "roles" / safe_name
    if not skill_path.parent.exists():
        skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(req.content, encoding="utf-8")
    return {"success": True, "filename": safe_name, "bytes": len(req.content.encode())}


@app.delete("/api/skills/{filename}")
async def delete_skill_file(filename: str):
    """Skill / Rol faylini o'chiradi."""
    safe_name = os.path.basename(filename.strip())
    if not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="Разрешены только .md файлы")
    skill_path = BASE_DIR / "roles" / safe_name
    if not skill_path.exists():
        raise HTTPException(status_code=404, detail=f"Файл не найден: {safe_name}")
    try:
        skill_path.unlink()
        return {"success": True, "message": f"Файл {safe_name} успешно удален"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось удалить файл: {str(e)}")

@app.delete("/api/md/{filepath:path}")
async def delete_md_file(filepath: str):
    """MD faylini o'chiradi."""
    clean = os.path.normpath(filepath.strip())
    if clean.startswith(".."):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    full_path = BASE_DIR / clean
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Файл не найден: {clean}")
    try:
        full_path.unlink()
        return {"success": True, "message": f"Документ {clean} успешно удален"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось удалить документ: {str(e)}")


# --- Markdown Editor Endpoints ---

@app.get("/api/md")
async def list_md_files():
    """Loyiha papkasidagi barcha .md fayllar ro'yxatini qaytaradi."""
    files = []
    # Scan BASE_DIR
    for root, dirs, filenames in os.walk(str(BASE_DIR)):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'venv', '.git')]
        for fname in filenames:
            if fname.endswith('.md') and not fname.startswith('.'):
                rel = os.path.relpath(os.path.join(root, fname), str(BASE_DIR))
                files.append(rel)
    # Also scan WORKSPACE_DIR
    if WORKSPACE_DIR.exists():
        for root, dirs, filenames in os.walk(str(WORKSPACE_DIR)):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'venv', '.git')]
            for fname in filenames:
                if fname.endswith('.md') and not fname.startswith('.'):
                    rel = "workspace/" + os.path.relpath(os.path.join(root, fname), str(WORKSPACE_DIR))
                    if rel not in files:
                        files.append(rel)
    files.sort()
    return {"files": files, "base_dir": str(BASE_DIR)}

@app.post("/api/md/create")
async def create_md_file_endpoint(req: CreateMdRequest):
    """Yangi MD fayl yaratadi."""
    clean_name = os.path.basename(req.filename.strip())
    if not clean_name.endswith('.md'):
        clean_name += '.md'
    full_path = BASE_DIR / clean_name
    full_path.write_text(req.content or f"# {clean_name[:-3]}\n\nНовый документ Markdown.\n", encoding="utf-8")
    return {"success": True, "filename": clean_name, "filepath": clean_name}

@app.get("/api/md/{filepath:path}")
async def get_md_file(filepath: str):
    """MD faylini o'qiydi."""
    clean = os.path.normpath(filepath.strip())
    if clean.startswith('..'):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    full_path = BASE_DIR / clean
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Файл не найден: {clean}")
    content = full_path.read_text(encoding="utf-8")
    return {"filepath": clean, "content": content}

@app.post("/api/md/{filepath:path}")
async def save_md_file(filepath: str, req: EditorSaveRequest):
    """MD faylini saqlaydi."""
    clean = os.path.normpath(filepath.strip())
    if clean.startswith('..'):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    full_path = BASE_DIR / clean
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(req.content, encoding="utf-8")
    return {"success": True, "filepath": clean, "bytes": len(req.content.encode())}

# --- Dynamic Provider Models Fetching Endpoints ---

@app.post("/api/models/fetch-from-provider")
async def fetch_models_from_provider_endpoint(req: FetchModelsRequest):
    """Har qanday tashqi OpenAI-mos yoki Ollama endpointidan modellar ro'yxatini yuklaydi."""
    res = await models_hub.fetch_models_from_provider(req.base_url, req.api_key or "")
    return res

@app.post("/api/models/import-custom")
async def import_custom_models_endpoint(req: ImportCustomModelsRequest):
    """Yuklangan modellarni tizim katalogiga qo'shadi."""
    models_hub.register_custom_provider(req.base_url, req.api_key or "", req.models)
    return {"success": True, "count": len(req.models)}

@app.get("/api/leaderboard")
@app.get("/api/skill-matrix/leaderboard")
async def get_leaderboard():
    return skill_matrix.get_leaderboard_payload()

# --- Workstations & Real Hive Stats ---

@app.get("/api/hive/stations")
async def get_hive_stations():
    return {
        "stations": list(WORKSTATIONS.values()),
        "real_stats": models_hub.get_real_hive_stats()
    }

@app.get("/api/hive/real-stats")
async def get_real_stats():
    return models_hub.get_real_hive_stats()

# --- Prompt Cache Endpoints ---

@app.get("/api/cache/stats")
async def get_cache_stats():
    return prompt_cache.get_stats()

@app.post("/api/cache/clear")
async def clear_cache():
    removed = prompt_cache.invalidate_all()
    return {"success": True, "removed_entries": removed}

# --- Agent Runtime Configuration ---

@app.get("/api/agent/config")
async def get_agent_config():
    return {"config": AGENT_CONFIG, "tools": get_tool_schemas()}

@app.post("/api/agent/config")
async def update_agent_config(payload: Dict[str, Any]):
    """Agent xatti-harakatini serverni qayta ishga tushirmasdan sozlash."""
    numeric = {
        "max_tool_steps": (1, 24), "max_repair_rounds": (0, 5),
        "repair_threshold": (0, 100), "llm_base_timeout_s": (10, 300),
        "llm_max_timeout_s": (30, 600), "llm_retries_per_model": (0, 5),
        "exploration_rate": (0.0, 1.0),
    }
    applied = {}
    for key, (low, high) in numeric.items():
        if key in payload:
            try:
                value = float(payload[key])
            except (TypeError, ValueError):
                continue
            value = max(low, min(high, value))
            AGENT_CONFIG[key] = int(value) if isinstance(AGENT_CONFIG.get(key), int) else value
            applied[key] = AGENT_CONFIG[key]
    return {"success": True, "applied": applied, "config": AGENT_CONFIG}

# --- Terminal Execution Endpoint ---

class TerminalRequest(BaseModel):
    command: str
    cwd: Optional[str] = None

@app.post("/api/terminal/exec")
async def exec_terminal(req: TerminalRequest):
    result = run_shell_command(req.command, req.cwd)
    return result

# --- Desktop Projects Endpoints ---

@app.get("/api/desktop/projects")
async def get_desktop_projects():
    projects = []
    try:
        if PROJECTS_BASE_DIR.exists():
            for p in PROJECTS_BASE_DIR.iterdir():
                if p.is_dir() and not p.name.startswith("."):
                    try:
                        files = [f.name for f in p.iterdir() if f.is_file() and not f.name.startswith(".")]
                        projects.append({
                            "name": p.name,
                            "path": str(p),
                            "files_count": len(files),
                            "files": files,
                            "modified": p.stat().st_mtime
                        })
                    except Exception:
                        pass
    except Exception:
        pass
    return {
        "base_path": str(PROJECTS_BASE_DIR),
        "total_projects": len(projects),
        "projects": sorted(projects, key=lambda x: x["modified"], reverse=True)
    }

# --- Models & Health Endpoints ---

@app.get("/api/models")
async def get_models():
    return {
        "models": models_hub.get_all_stats(),
        "providers": PROVIDERS
    }

@app.post("/api/models/ping-all")
async def ping_all():
    results = await models_hub.ping_all_models(CUSTOM_KEYS)
    return {"results": results}

class SinglePingRequest(BaseModel):
    model_id: str

@app.post("/api/models/ping-single")
async def ping_single(req: SinglePingRequest):
    result = await models_hub.ping_model(req.model_id, CUSTOM_KEYS)
    return result

# --- Workspace & File Management ---

@app.get("/api/tools")
async def get_tools():
    # `AVAILABLE_TOOLS` ichida Python funksiyalari bor — ularni to'g'ridan-to'g'ri
    # qaytarish JSON serializatsiyasini buzardi. Faqat sxemalarni qaytaramiz.
    return {"tools": get_tool_schemas()}

@app.get("/api/workspace/files")
async def get_workspace_files():
    return list_files()

@app.get("/api/workspace/tree")
async def get_workspace_tree():
    """
    Aktiv loyiha papkasi va workspace daraxtini ierarxik ko'rinishda qaytaradi.
    Frontend jonli fayllar daraxtini shu ma'lumot bilan quradi va SSE `fs_change`
    eventlari orqali yangilab boradi.
    """
    def build_tree(root: Path, label: str):
        if not root.exists() or not root.is_dir():
            return {"name": label, "path": str(root), "type": "root", "children": [], "exists": False}

        found, truncated = walk_project_files(root, limit=MAX_WALK_FILES, include_dirs=True)
        node_map: Dict[str, Dict[str, Any]] = {}
        children_root: List[Dict[str, Any]] = []

        for path, rel in sorted(found, key=lambda x: (x[1].count("/"), x[1])):
            parts = rel.split("/")
            parent_children = children_root
            acc = []
            for i, part in enumerate(parts):
                acc.append(part)
                key = "/".join(acc)
                existing = node_map.get(key)
                if existing:
                    parent_children = existing["children"] if existing["type"] == "dir" else parent_children
                    continue
                is_last = (i == len(parts) - 1)
                is_dir = path.is_dir() if is_last else True
                try:
                    size = path.stat().st_size if (is_last and not is_dir) else 0
                except Exception:
                    size = 0
                node = {
                    "name": part,
                    "path": key,
                    "type": "dir" if is_dir else "file",
                    "size": size,
                    "children": [] if is_dir else None,
                }
                node_map[key] = node
                parent_children.append(node)
                if is_dir:
                    parent_children = node["children"]

        return {
            "name": label,
            "path": str(root),
            "type": "root",
            "exists": True,
            "truncated": truncated,
            "children": children_root,
        }

    active = get_active_project_dir()
    return {
        "active_project": build_tree(active, active.name or "loyiha"),
        "workspace": build_tree(WORKSPACE_DIR, "workspace"),
        "active_project_dir": str(active),
        "workspace_dir": str(WORKSPACE_DIR),
    }

@app.get("/api/workspace/files/{filename:path}")
async def get_workspace_file_by_path(filename: str):
    return read_file(filename)

@app.get("/api/workspace/file")
async def get_workspace_file(name: str):
    return read_file(name)

@app.delete("/api/workspace/file")
async def delete_workspace_file(name: str):
    clean_name = os.path.basename(name.strip())
    target = WORKSPACE_DIR / clean_name
    if target.exists():
        target.unlink()
        return {"success": True, "message": f"Fayl o'chirildi: {clean_name}"}
    raise HTTPException(status_code=404, detail="Fayl topilmadi")

# --- Settings & Setup Wizard Endpoints ---

@app.get("/api/settings/keys")
async def get_keys():
    return {
        "gemini": CUSTOM_KEYS["gemini"][:8] + "..." if CUSTOM_KEYS.get("gemini") else "",
        "17_wtf": CUSTOM_KEYS["17_wtf"][:8] + "..." if CUSTOM_KEYS.get("17_wtf") else "",
        "openrouter": CUSTOM_KEYS["openrouter"][:8] + "..." if CUSTOM_KEYS.get("openrouter") else "",
        "openai": CUSTOM_KEYS.get("openai", "")[:8] + "..." if CUSTOM_KEYS.get("openai") else "",
        "groq": CUSTOM_KEYS.get("groq", "")[:8] + "..." if CUSTOM_KEYS.get("groq") else ""
    }

class SetupConfigRequest(BaseModel):
    mode: str = "single"  # "single", "multi", "custom"
    provider: Optional[str] = "openrouter"
    openrouter_key: Optional[str] = None
    github_key: Optional[str] = None
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    groq_key: Optional[str] = None
    custom_base_url: Optional[str] = None
    custom_key: Optional[str] = None
    projects_dir: Optional[str] = None

@app.post("/api/setup/configure")
async def save_setup_configuration(req: SetupConfigRequest):
    if req.github_key:
        CUSTOM_KEYS["github"] = req.github_key.strip()
    if req.gemini_key:
        CUSTOM_KEYS["gemini"] = req.gemini_key.strip()
    if req.openrouter_key:
        CUSTOM_KEYS["openrouter"] = req.openrouter_key.strip()
        CUSTOM_KEYS["17_wtf"] = req.openrouter_key.strip()
    if req.openai_key:
        CUSTOM_KEYS["openai"] = req.openai_key.strip()
    if req.groq_key:
        CUSTOM_KEYS["groq"] = req.groq_key.strip()
    if req.custom_key:
        CUSTOM_KEYS["custom"] = req.custom_key.strip()

    env_path = BASE_DIR / ".env"
    lines = [
        "# Ant Colony AI Environment Configuration",
        f"SETUP_MODE={req.mode}",
        f"PRIMARY_PROVIDER={req.provider}",
        f"GITHUB_TOKEN={req.github_key or ''}",
        f"OPENROUTER_API_KEY={req.openrouter_key or ''}",
        f"GEMINI_API_KEY={req.gemini_key or ''}",
        f"OPENAI_API_KEY={req.openai_key or ''}",
        f"GROQ_API_KEY={req.groq_key or ''}",
        f"CUSTOM_BASE_URL={req.custom_base_url or ''}",
        f"CUSTOM_API_KEY={req.custom_key or ''}",
        f"PROJECTS_BASE_DIR={req.projects_dir or str(PROJECTS_BASE_DIR)}",
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"success": True, "message": "Конфигурация успешно сохранена и активирована."}

@app.get("/api/setup/status")
async def get_setup_status():
    has_any_key = any(bool(v) for k, v in CUSTOM_KEYS.items() if v) or bool(os.getenv("GROQ_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("GITHUB_TOKEN") or os.getenv("GEMINI_API_KEY"))
    active_providers = [k for k, v in CUSTOM_KEYS.items() if v]
    if not active_providers and os.getenv("GROQ_API_KEY"):
        active_providers.append("groq")
    active_dir = get_active_project_dir()
    janitor_stats = _JANITOR.snapshot() if _JANITOR else {}
    return {
        "configured": has_any_key,
        "providers_active": active_providers,
        "projects_dir": str(_config_module.PROJECTS_BASE_DIR),
        "active_project_dir": str(active_dir),
        "workspace_dir": str(WORKSPACE_DIR),
        "projects_dir_exists": Path(_config_module.PROJECTS_BASE_DIR).exists(),
        "janitor": janitor_stats,
    }


class TestKeyRequest(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None


@app.post("/api/setup/test-key")
async def test_api_key(req: TestKeyRequest):
    """
    Provayder API kalitini bitta yengil so'rov bilan tekshiradi (models list).
    UI'da har bir kalit yonida "Проверить" tugmasi shu endpoint'ga murojaat qiladi.
    """
    import aiohttp
    prov = (req.provider or "").lower().strip()
    key = (req.api_key or "").strip()
    if not key:
        return {"success": False, "error": "API kalit bo'sh"}

    if prov == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        headers = {}
    elif prov == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif prov == "openai":
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif prov == "groq":
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif prov == "github":
        url = "https://models.inference.ai.azure.com/models"
        headers = {"Authorization": f"Bearer {key}", "api-version": "2024-08-01-preview"}
    elif prov == "17_wtf":
        url = "https://api.17.wtf/api/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif prov == "custom" and req.base_url:
        url = req.base_url.rstrip("/") + "/models"
        headers = {"Authorization": f"Bearer {key}"} if key and key != "ollama" else {}
    else:
        return {"success": False, "error": f"Noma'lum provayder: {prov}"}

    try:
        timeout = aiohttp.ClientTimeout(total=10, sock_connect=5, sock_read=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    count = len(body.get("data") or body.get("models") or [])
                    return {"success": True, "provider": prov, "status": 200,
                            "models_visible": count,
                            "message": f"Успешно · доступно моделей: {count}"}
                text = (await resp.text())[:200]
                return {"success": False, "provider": prov, "status": resp.status,
                        "error": f"HTTP {resp.status}: {text}"}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Тайм-аут (>10s) — проверьте сеть"}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


class WorkspaceDirRequest(BaseModel):
    path: str
    create_if_missing: bool = True


@app.post("/api/setup/workspace-dir")
async def set_workspace_dir(req: WorkspaceDirRequest):
    """
    Loyihalar saqlanadigan katalogni almashtiradi (jonli — restart kerak emas).
    Har yangi loyiha shu papkaning ichida yaratiladi.
    """
    raw = (req.path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Papka manzili bo'sh")
    p = Path(os.path.expanduser(raw)).resolve()
    if req.create_if_missing:
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Papka yaratilmadi: {e}")
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Papka topilmadi: {p}")

    # Global config'ni yangilaymiz
    _config_module.PROJECTS_BASE_DIR = p
    # tools.py'dagi aktiv katalogni ham (agar hech qanday konkret loyiha ochilmagan bo'lsa) yangilaymiz
    if get_active_project_dir() == Path(str(_config_module.PROJECTS_BASE_DIR)):
        set_active_project_dir(p)
    else:
        set_active_project_dir(p)

    # .env'ga yozamiz (keyingi ishga tushirishda ham eslab qolsin)
    _persist_env_key("PROJECTS_BASE_DIR", str(p))

    return {
        "success": True,
        "projects_dir": str(p),
        "exists": True,
        "message": "Katalog yangilandi. Yangi loyihalar shu papkada yaratiladi."
    }


def _persist_env_key(key: str, value: str):
    """`.env` faylida bitta kalitni yangilaydi (yoki qo'shadi). Boshqalari tegilmaydi."""
    env_path = BASE_DIR / ".env"
    lines: List[str] = []
    found = False
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []
    for i, ln in enumerate(lines):
        if ln.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    try:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


class FreeModelsRequest(BaseModel):
    provider: str = "openrouter"
    api_key: Optional[str] = None


@app.post("/api/setup/fetch-free-models")
async def fetch_free_models(req: FreeModelsRequest):
    """
    Provayderdan faqat BEPUL modellarni yuklaydi (OpenRouter uchun `:free` suffix
    yoki pricing == 0, boshqa provayderlar uchun ochiq katalog).
    """
    import aiohttp
    prov = (req.provider or "").lower()
    key = (req.api_key or CUSTOM_KEYS.get(prov, "")).strip()

    if prov == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {key}"} if key else {}
    elif prov == "groq":
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif prov == "gemini":
        # Gemini free tier (gemini-2.5-flash-lite, gemini-1.5-flash-8b, gemini-2.5-pro-preview kabi)
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        headers = {}
    else:
        raise HTTPException(status_code=400, detail=f"'{prov}' bepul model ro'yxatini qo'llamaydi")

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    text = (await resp.text())[:300]
                    return {"success": False, "error": f"HTTP {resp.status}: {text}"}
                body = await resp.json()
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}

    free_models: List[Dict[str, Any]] = []
    if prov == "openrouter":
        for m in body.get("data", []):
            mid = m.get("id", "")
            pricing = m.get("pricing") or {}
            prompt_cost = float(pricing.get("prompt") or 0)
            completion_cost = float(pricing.get("completion") or 0)
            is_free = mid.endswith(":free") or (prompt_cost == 0 and completion_cost == 0)
            if is_free:
                free_models.append({
                    "id": mid,
                    "name": m.get("name") or mid,
                    "context_window": m.get("context_length") or 8192,
                    "max_output": (m.get("top_provider") or {}).get("max_completion_tokens") or 4096,
                    "features": [f for f in [
                        "Vision" if (m.get("architecture") or {}).get("modality", "").startswith("multimodal") else None,
                        "Free"
                    ] if f],
                    "supports_reasoning": bool(m.get("supported_parameters") and "reasoning" in (m.get("supported_parameters") or [])),
                    "is_free": True,
                    "pricing": pricing,
                })
    elif prov == "groq":
        # Groq'da hozircha barcha modellar bepul (free tier limit bilan)
        for m in body.get("data", []):
            free_models.append({
                "id": m.get("id"),
                "name": m.get("id"),
                "context_window": m.get("context_window") or 8192,
                "is_free": True,
            })
    elif prov == "gemini":
        # Gemini free tier — faqat "flash" va "flash-lite" bilan boshlangan modellar
        for m in body.get("models", []):
            name = m.get("name", "").replace("models/", "")
            if "flash" in name.lower() or "flash-lite" in name.lower():
                free_models.append({
                    "id": name,
                    "name": m.get("displayName") or name,
                    "context_window": m.get("inputTokenLimit") or 32768,
                    "max_output": m.get("outputTokenLimit") or 8192,
                    "features": [t for t in (m.get("supportedGenerationMethods") or [])],
                    "is_free": True,
                })

    return {
        "success": True,
        "provider": prov,
        "count": len(free_models),
        "models": free_models,
    }


class GenSettingsRequest(BaseModel):
    default_temperature: Optional[float] = None
    default_max_tokens: Optional[int] = None
    enable_vision: Optional[bool] = None
    free_models_only: Optional[bool] = None


@app.post("/api/setup/generation-settings")
async def update_generation_settings(req: GenSettingsRequest):
    """Setup wizard'dan LLM generation defaults'ni jonli o'zgartiradi."""
    applied = {}
    if req.default_temperature is not None:
        v = max(0.0, min(1.5, float(req.default_temperature)))
        AGENT_CONFIG["default_temperature"] = v
        applied["default_temperature"] = v
    if req.default_max_tokens is not None:
        v = max(256, min(65536, int(req.default_max_tokens)))
        AGENT_CONFIG["default_max_tokens"] = v
        applied["default_max_tokens"] = v
    if req.enable_vision is not None:
        AGENT_CONFIG["enable_vision"] = bool(req.enable_vision)
        applied["enable_vision"] = bool(req.enable_vision)
    if req.free_models_only is not None:
        AGENT_CONFIG["free_models_only"] = bool(req.free_models_only)
        applied["free_models_only"] = bool(req.free_models_only)

    # .env'ga ham yozamiz
    for k, v in applied.items():
        _persist_env_key(f"AGENT_{k.upper()}", str(v))

    return {"success": True, "applied": applied, "config": {
        k: AGENT_CONFIG[k] for k in ["default_temperature", "default_max_tokens", "enable_vision", "free_models_only"]
    }}


@app.get("/api/setup/generation-settings")
async def get_generation_settings():
    """Setup wizard uchun joriy generation sozlamalari."""
    return {
        "default_temperature": AGENT_CONFIG.get("default_temperature", 0.2),
        "default_max_tokens": AGENT_CONFIG.get("default_max_tokens", 8192),
        "enable_vision": AGENT_CONFIG.get("enable_vision", True),
        "free_models_only": AGENT_CONFIG.get("free_models_only", False),
    }


class BrowseDirRequest(BaseModel):
    path: str


@app.post("/api/setup/browse-dir")
async def browse_dir(req: BrowseDirRequest):
    """
    Serverda katalog navigatsiyasi (setup wizard uchun sodda file browser).
    Faqat papkalarni qaytaradi.
    """
    raw = (req.path or "").strip() or "~"
    p = Path(os.path.expanduser(raw)).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Papka topilmadi: {p}")
    if not p.is_dir():
        p = p.parent
    entries = []
    try:
        for e in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            if e.name.startswith("."):
                continue
            if e.is_dir():
                entries.append({"name": e.name, "path": str(e), "type": "dir"})
    except PermissionError:
        raise HTTPException(status_code=403, detail="Kirish rad etildi")
    return {"path": str(p), "parent": str(p.parent), "entries": entries}

# --- Decoupled Background Orchestrator Engine ---

class OrchestrationJob:
    def __init__(self, job_id: str, task: str):
        self.job_id = job_id
        self.task = task
        self.status = "running"  # "running", "completed", "failed", "cancelled"
        self.events: List[Dict[str, Any]] = []
        self.subscribers: List[asyncio.Queue] = []
        self.final_event: Optional[Dict[str, Any]] = None
        self.created_at = time.time()
        self.finished_at: Optional[float] = None
        self.asyncio_task: Optional[asyncio.Task] = None

    def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass

    async def run(self):
        # Live event emitter — tools.py'dagi fayl va terminal chiqishlari shu
        # orqali jonli SSE stream'ga tushadi. Faqat shu orkestratsiya vaqtida
        # faol; tugagach avtomatik o'chiriladi.
        set_event_emitter(self.add_event)
        try:
            self.add_event({"type": "user_task", "task": self.task, "timestamp": time.time()})
            async for event in agent_engine.run_orchestrated_task_stream(
                task_prompt=self.task,
                custom_keys=CUSTOM_KEYS
            ):
                if self.status == "cancelled":
                    break
                self.add_event(event)
                if event.get("type") == "orchestration_completed":
                    self.status = "completed"
                    self.final_event = event
                    # PM xotirasiga yozamiz — keyingi sessiyalarda kontekst sifatida
                    try:
                        mem = get_memory()
                        if mem:
                            eval_summary = event.get("eval_summary") or {}
                            mem.record_orchestration(
                                task=self.task,
                                project_dir=event.get("project_dir"),
                                files=event.get("created_files") or [],
                                score=event.get("final_score"),
                                duration_s=event.get("duration_seconds") or (time.time() - self.created_at),
                                summary=(eval_summary.get("summary") if isinstance(eval_summary, dict) else None),
                            )
                    except Exception:
                        pass

            if self.status not in ("completed", "cancelled", "failed"):
                self.status = "completed"
        except asyncio.CancelledError:
            self.status = "cancelled"
        except Exception as e:
            self.status = "failed"
            err_ev = {
                "type": "orchestration_failed",
                "error": f"{type(e).__name__}: {e}",
                "final_content": f"### Ошибка выполнения оркестрации\n\n`{type(e).__name__}: {e}`",
            }
            self.final_event = err_ev
            self.add_event(err_ev)
        finally:
            set_event_emitter(None)
            self.finished_at = time.time()
            # Send completion signal to all queues
            for q in list(self.subscribers):
                try:
                    q.put_nowait({"type": "_stream_end"})
                except Exception:
                    pass

ACTIVE_JOBS: Dict[str, OrchestrationJob] = {}
CURRENT_JOB: Optional[OrchestrationJob] = None

class OrchestratorRequest(BaseModel):
    task: str

@app.get("/api/orchestrator/latest")
async def get_latest_orchestration():
    global CURRENT_JOB
    if not CURRENT_JOB:
        return {"job_id": None, "task": "", "status": "idle", "events": [], "final_event": None}
    return {
        "job_id": CURRENT_JOB.job_id,
        "task": CURRENT_JOB.task,
        "status": CURRENT_JOB.status,
        "events": CURRENT_JOB.events,
        "final_event": CURRENT_JOB.final_event,
        "created_at": CURRENT_JOB.created_at,
        "finished_at": CURRENT_JOB.finished_at
    }

@app.post("/api/orchestrator/cancel")
async def cancel_active_orchestration():
    global CURRENT_JOB
    if CURRENT_JOB and CURRENT_JOB.status == "running":
        CURRENT_JOB.status = "cancelled"
        if CURRENT_JOB.asyncio_task and not CURRENT_JOB.asyncio_task.done():
            CURRENT_JOB.asyncio_task.cancel()
        return {"success": True, "message": "Vazifa bekor qilindi."}
    return {"success": False, "message": "Faol vazifa topilmadi."}

@app.post("/api/orchestrator/dispatch")
async def dispatch_orchestrator(req: OrchestratorRequest):
    """
    Spawns an independent background orchestration job on the server.
    Clients can disconnect, refresh, and reconnect without cancelling the task!
    """
    global CURRENT_JOB
    job_id = f"job_{int(time.time()*1000)}"
    job = OrchestrationJob(job_id=job_id, task=req.task)
    ACTIVE_JOBS[job_id] = job
    CURRENT_JOB = job

    # Start background task decoupled from HTTP connection
    job.asyncio_task = asyncio.create_task(job.run())

    return await stream_job_events(job)

@app.get("/api/orchestrator/stream")
@app.get("/api/orchestrator/stream/{job_id}")
async def stream_existing_job(job_id: Optional[str] = None):
    global CURRENT_JOB
    target_job = ACTIVE_JOBS.get(job_id) if job_id else CURRENT_JOB
    if not target_job:
        raise HTTPException(status_code=404, detail="Faol vazifa topilmadi")
    return await stream_job_events(target_job)

async def stream_job_events(job: OrchestrationJob):
    async def event_generator():
        q = asyncio.Queue()
        job.subscribers.append(q)

        try:
            # 1. Replay past events first so reconnecting clients catch up instantly
            for ev in list(job.events):
                payload = json.dumps(ev, ensure_ascii=False, default=str)
                yield f"data: {payload}\n\n"

            # If job already completed, finish stream
            if job.status in ("completed", "failed", "cancelled"):
                return

            # 2. Stream live incoming events
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=25.0)
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat comment
                    yield ": ping\n\n"
                    if job.status in ("completed", "failed", "cancelled"):
                        break
                    continue

                if ev.get("type") == "_stream_end" or job.status in ("completed", "failed", "cancelled"):
                    if ev.get("type") != "_stream_end":
                        payload = json.dumps(ev, ensure_ascii=False, default=str)
                        yield f"data: {payload}\n\n"
                    break

                payload = json.dumps(ev, ensure_ascii=False, default=str)
                yield f"data: {payload}\n\n"
        except asyncio.CancelledError:
            # Client disconnected / refreshed — DO NOT cancel the job!
            pass
        finally:
            if q in job.subscribers:
                job.subscribers.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# --- PM Memory Endpoints ---

@app.get("/api/pm/memory")
async def pm_memory_get():
    mem = get_memory()
    if not mem:
        return {"error": "memory not initialized"}
    return mem.snapshot()


@app.get("/api/pm/memory/greeting")
async def pm_memory_greeting():
    """Idle payt PM aytadigan dinamik xabar uchun ma'lumotlar."""
    mem = get_memory()
    if not mem:
        return {"total_orchestrations": 0, "last_project": None, "pending_plans": []}
    return mem.build_idle_greeting()


class FuturePlanRequest(BaseModel):
    text: str
    source: str = "user"


@app.post("/api/pm/memory/future-plan")
async def pm_memory_add_plan(req: FuturePlanRequest):
    mem = get_memory()
    if not mem:
        raise HTTPException(status_code=503, detail="memory not initialized")
    mem.add_future_plan(req.text, req.source)
    return {"success": True, "count": len(mem.snapshot()["future_plans"])}


class RemovePlanRequest(BaseModel):
    index: int


@app.post("/api/pm/memory/remove-plan")
async def pm_memory_remove_plan(req: RemovePlanRequest):
    mem = get_memory()
    if not mem:
        raise HTTPException(status_code=503, detail="memory not initialized")
    mem.remove_future_plan(req.index)
    return {"success": True}


class PreferenceRequest(BaseModel):
    key: str
    value: Any


@app.post("/api/pm/memory/preference")
async def pm_memory_pref(req: PreferenceRequest):
    mem = get_memory()
    if not mem:
        raise HTTPException(status_code=503, detail="memory not initialized")
    mem.set_preference(req.key, req.value)
    return {"success": True}


@app.post("/api/pm/memory/clear")
async def pm_memory_clear():
    mem = get_memory()
    if not mem:
        raise HTTPException(status_code=503, detail="memory not initialized")
    mem.clear(keep_preferences=True)
    return {"success": True}


# --- Workspace Janitor Endpoints ---

@app.get("/api/janitor/status")
async def janitor_status():
    if not _JANITOR:
        return {"enabled": False, "message": "Janitor faol emas"}
    return {**_JANITOR.snapshot(), "log_tail": _JANITOR.read_recent_log(20)}


@app.post("/api/janitor/force-scan")
async def janitor_force_scan():
    if not _JANITOR:
        raise HTTPException(status_code=503, detail="Janitor faol emas")
    return _JANITOR.force_scan()


class JanitorToggleRequest(BaseModel):
    enabled: bool


@app.post("/api/janitor/toggle")
async def janitor_toggle(req: JanitorToggleRequest):
    if not _JANITOR:
        raise HTTPException(status_code=503, detail="Janitor faol emas")
    _JANITOR.ENABLED = bool(req.enabled)
    return {"enabled": _JANITOR.ENABLED}


# --- Deploy Endpoints (GitHub & Netlify) ---

class GitHubDeployRequest(BaseModel):
    token: str
    project_name: str  # 04_Loyihalar ichidagi papka nomi
    repo_name: str
    description: Optional[str] = ""
    private: bool = False
    commit_message: Optional[str] = "Initial commit via Ant Colony AI"


class NetlifyDeployRequest(BaseModel):
    token: str
    project_name: str
    site_name: Optional[str] = None   # yo'q bo'lsa Netlify tasodifiy nom beradi


def _project_dir_or_error(project_name: str) -> Path:
    """Xavfsiz tarzda loyiha papkasini tanlaydi (path traversal himoyasi bilan)."""
    clean = os.path.basename((project_name or "").strip())
    if not clean:
        raise HTTPException(status_code=400, detail="project_name bo'sh")
    target = PROJECTS_BASE_DIR / clean
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f"Loyiha topilmadi: {clean}")
    return target


@app.get("/api/deploy/projects")
async def list_deployable_projects():
    """04_Loyihalar ichidagi barcha papkalarni deploy uchun ro'yxatlash."""
    items = []
    if PROJECTS_BASE_DIR.exists():
        for p in PROJECTS_BASE_DIR.iterdir():
            if not (p.is_dir() and not p.name.startswith(".")):
                continue
            try:
                # Faqat kod fayllari borligini tekshiramiz — bo'sh papka deploy'ga foyda bermaydi
                has_files = any(True for f in p.iterdir() if f.is_file())
                items.append({
                    "name": p.name,
                    "path": str(p),
                    "has_files": has_files,
                    "modified": p.stat().st_mtime,
                    "has_git": (p / ".git").exists(),
                })
            except Exception:
                continue
    items.sort(key=lambda x: x["modified"], reverse=True)
    return {"projects": items}


@app.post("/api/deploy/github")
async def deploy_to_github(req: GitHubDeployRequest):
    """
    GitHub'da yangi repo yaratadi va joriy loyiha papkasini push qiladi.
    Talab: PAT `repo` scope bilan.
    """
    import aiohttp
    target = _project_dir_or_error(req.project_name)
    token = (req.token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token yo'q")
    repo_name = re.sub(r"[^a-zA-Z0-9_.-]", "-", (req.repo_name or "").strip())
    if not repo_name:
        raise HTTPException(status_code=400, detail="repo_name yaroqsiz")

    steps: List[Dict[str, Any]] = []

    # 1. Repo yaratish
    async with aiohttp.ClientSession() as session:
        payload = {
            "name": repo_name,
            "description": req.description or "",
            "private": bool(req.private),
            "auto_init": False,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AntColonyAI-Deployer",
        }
        async with session.post("https://api.github.com/user/repos",
                                json=payload, headers=headers) as resp:
            body = await resp.json()
            if resp.status not in (200, 201):
                msg = body.get("message") or str(body)[:200]
                steps.append({"step": "create_repo", "ok": False, "error": msg, "status": resp.status})
                # Repo allaqachon mavjud bo'lsa — user'ga tegishli bo'lsa foydalanamiz
                if resp.status == 422 and "already exists" in msg.lower():
                    steps[-1]["note"] = "Repo allaqachon mavjud — push davom etadi"
                else:
                    return {"success": False, "steps": steps, "error": msg}
            else:
                steps.append({"step": "create_repo", "ok": True, "html_url": body.get("html_url"),
                              "clone_url": body.get("clone_url")})

        # username'ni olish (remote URL uchun)
        async with session.get("https://api.github.com/user", headers=headers) as u_resp:
            u_body = await u_resp.json()
            username = u_body.get("login")
            if not username:
                return {"success": False, "steps": steps, "error": "GitHub username aniqlanmadi"}

    remote_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    safe_remote = f"https://github.com/{username}/{repo_name}"

    # 2. Git init / push (loop ichida shell buyruqlar bilan)
    git_cmds = [
        ("git init -b main", "git_init"),
        ('git config user.email "ant-colony@local"', "git_email"),
        ('git config user.name "Ant Colony AI"', "git_name"),
        ("git add -A", "git_add"),
        (f'git commit -m "{req.commit_message}" --allow-empty', "git_commit"),
        (f'git remote remove origin 2>/dev/null; git remote add origin {remote_url}', "git_remote"),
        ("git push -u origin main --force", "git_push"),
    ]

    def _sanitize(text: str) -> str:
        # Token oshkor bo'lmasligi uchun
        if not text:
            return ""
        return text.replace(token, "***TOKEN***")

    def _run_git(cmd: str) -> Dict[str, Any]:
        try:
            r = subprocess.run(cmd, shell=True, cwd=str(target),
                               capture_output=True, text=True, timeout=90)
            return {
                "returncode": r.returncode,
                "stdout": _sanitize(r.stdout.strip())[:400],
                "stderr": _sanitize(r.stderr.strip())[:600],
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "timeout (>90s)"}
        except Exception as e:
            return {"returncode": -1, "stdout": "", "stderr": f"{type(e).__name__}: {e}"}

    for cmd, label in git_cmds:
        res = _run_git(cmd)
        ok = res["returncode"] == 0
        steps.append({
            "step": label, "ok": ok, "command": _sanitize(cmd),
            "returncode": res["returncode"],
            "stdout": res["stdout"], "stderr": res["stderr"],
        })
        # commit'da hech qanday o'zgarish bo'lmasa ham davom etamiz
        if not ok and label not in ("git_commit", "git_remote"):
            return {"success": False, "steps": steps, "error": f"{label} muvaffaqiyatsiz"}

    return {
        "success": True,
        "html_url": safe_remote,
        "clone_url": f"https://github.com/{username}/{repo_name}.git",
        "steps": steps,
    }


@app.post("/api/deploy/netlify")
async def deploy_to_netlify(req: NetlifyDeployRequest):
    """
    Loyihani zip'ga o'rab, Netlify API orqali yangi sayt sifatida deploy qiladi.
    Talab: Netlify PAT `deploy` yoki `full_access` bilan.
    """
    import aiohttp
    import io
    import zipfile

    target = _project_dir_or_error(req.project_name)
    token = (req.token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Netlify token yo'q")

    # 1. Zip yaratish (workspace, node_modules va boshqa keraksiz papkalarsiz)
    buf = io.BytesIO()
    skipped = 0
    included = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        found, _ = walk_project_files(target, limit=5000, max_depth=10, include_dirs=False)
        for path, rel in found:
            try:
                if path.stat().st_size > 25 * 1024 * 1024:  # 25 MB
                    skipped += 1
                    continue
                zf.write(str(path), arcname=rel)
                included += 1
            except Exception:
                skipped += 1
                continue
    if included == 0:
        raise HTTPException(status_code=400, detail="Loyihada deploy qilish uchun fayl yo'q")
    buf.seek(0)
    zip_data = buf.getvalue()

    headers = {"Authorization": f"Bearer {token}"}
    site_id: Optional[str] = None
    site_name = re.sub(r"[^a-z0-9-]", "-", (req.site_name or "").lower().strip()) or None

    async with aiohttp.ClientSession() as session:
        # 2. Site yaratish (agar nom berilgan bo'lsa — subdomain sifatida)
        create_payload = {"name": site_name} if site_name else {}
        async with session.post("https://api.netlify.com/api/v1/sites",
                                json=create_payload, headers=headers) as resp:
            if resp.status not in (200, 201):
                err = await resp.text()
                return {"success": False, "error": f"Netlify site yaratilmadi ({resp.status}): {err[:200]}"}
            body = await resp.json()
            site_id = body["id"]
            site_url = body.get("ssl_url") or body.get("url")
            admin_url = body.get("admin_url")

        # 3. Zip'ni deploy qilish
        deploy_headers = dict(headers)
        deploy_headers["Content-Type"] = "application/zip"
        async with session.post(
            f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
            data=zip_data, headers=deploy_headers,
        ) as resp:
            if resp.status not in (200, 201):
                err = await resp.text()
                return {"success": False, "error": f"Deploy xatosi ({resp.status}): {err[:200]}",
                        "site_id": site_id, "admin_url": admin_url}
            deploy = await resp.json()

    return {
        "success": True,
        "site_id": site_id,
        "site_url": site_url,
        "admin_url": admin_url,
        "deploy_id": deploy.get("id"),
        "deploy_state": deploy.get("state"),
        "files_included": included,
        "files_skipped": skipped,
        "zip_size_bytes": len(zip_data),
    }


# --- Mount Static Files ---

STATIC_DIR = BASE_DIR / "static"
# --- Single-Line Code Obfuscation & Minification Router ---
def _minify_code_stream(content: str, content_type: str = "text/html") -> str:
    """Kommentlar va bo'shliqlarni zichlab, bitta uzun qatorda xavfsiz qaytaradi."""
    if "html" in content_type:
        # Strip HTML comments
        content = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.DOTALL)
        # Collapse multi-line whitespace
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        return " ".join(lines)
    elif "javascript" in content_type or "js" in content_type:
        # Strip block comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Strip single line comments that are safe
        lines = []
        for line in content.split('\n'):
            line_str = line.strip()
            if line_str.startswith('//') and not line_str.startswith('///'):
                continue
            if line_str:
                lines.append(line_str)
        return " ".join(lines)
    elif "css" in content_type:
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        return " ".join(lines)
    return content

@app.get("/", response_class=HTMLResponse)
async def index_root():
    """Bosh sahifani zichlangan bitta qatorda xavfsiz qaytaradi."""
    html_file = STATIC_DIR / "index.html"
    if html_file.exists():
        raw_html = html_file.read_text(encoding="utf-8")
        minified_html = _minify_code_stream(raw_html, "text/html")
        return HTMLResponse(content=minified_html, headers={"Content-Type": "text/html; charset=utf-8", "X-Content-Type-Options": "nosniff"})
    return HTMLResponse("<h1>Ant Colony</h1>")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    return FileResponse(str(index_file))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)


from pm_proactive import pm_proactive_engine

class PMFeedbackRequest(BaseModel):
    question_id: str
    question_text: str
    answer_chosen: str

class PMDocGenerateRequest(BaseModel):
    filename: str

@app.get("/api/pm/proactive")
async def get_pm_proactive_data():
    """PM proaktiv takliflari va CEO savollarini qaytaradi."""
    return pm_proactive_engine.get_proactive_insights()

@app.post("/api/pm/feedback")
async def post_pm_feedback(req: PMFeedbackRequest):
    """CEO javobini PM xotirasiga saqlaydi."""
    res = pm_proactive_engine.record_ceo_feedback(req.question_id, req.question_text, req.answer_chosen)
    return res

@app.post("/api/pm/generate-doc")
async def post_pm_generate_doc(req: PMDocGenerateRequest):
    """PM tavsiya qilgan MD hujjatini avtomatik yaratadi."""
    res = pm_proactive_engine.generate_recommended_doc(req.filename)
    return res

# --- Dynamic AI Joke Generator with LRU Non-Repeating Pool ---
_SERVED_JOKES_HISTORY = set()
_DYNAMIC_AI_JOKES_CACHE = []

STATIC_DEV_JOKES_POOL = [
    # Coder & QA
    {"speaker_a": "coder", "speaker_b": "tester", "text_a": "QA, я написал 500 строк кода без единого бага!", "text_b": "Отлично! Сейчас я отправлю пустой массив и нажму Enter 100 раз.", "tokens": 24},
    {"speaker_a": "tester", "speaker_b": "coder", "text_a": "Захожу в бар, заказываю: 1 кружку, 0 кружек, 999999 кружек, NULL кружек.", "text_b": "И бар выдержал? А потом пришел клиент и спросил, где туалет...", "tokens": 28},
    {"speaker_a": "coder", "speaker_b": "tester", "text_a": "Этот баг невозможно воспроизвести на моей локальной машине!", "text_b": "Тогда отдадим твой MacBook клиенту в качестве продакшн сервера.", "tokens": 22},
    {"speaker_a": "tester", "speaker_b": "coder", "text_a": "Я нашел критическую ошибку в релизной ветке.", "text_b": "Это не баг, это недокументированная фича для опытных пользователей.", "tokens": 25},
    {"speaker_a": "coder", "speaker_b": "tester", "text_a": "Мои unit-тесты покрывают 100% кода!", "text_b": "Но проверяют только то, что 2 + 2 = 4, верно?", "tokens": 21},

    # DevOps & Coder
    {"speaker_a": "deployer", "speaker_b": "coder", "text_a": "Кто запустил деплой в пятницу в 18:00?!", "text_b": "Я просто хотел протестировать CI/CD пайплайн перед выходными...", "tokens": 23},
    {"speaker_a": "deployer", "speaker_b": "coder", "text_a": "Почему Docker образ весит 4.8 гигабайта?", "text_b": "Там просто node_modules и немного душевного тепла.", "tokens": 24},
    {"speaker_a": "coder", "speaker_b": "deployer", "text_a": "Kubernetes под снова упал с ошибкой OOMKilled!", "text_b": "Дай ему еще 16 гигабайт оперативной памяти, пусть подавится.", "tokens": 26},
    {"speaker_a": "deployer", "speaker_b": "coder", "text_a": "Мы переходим на serverless архитектуру.", "text_b": "Значит, теперь наши баги будут масштабироваться автоматически?", "tokens": 22},
    {"speaker_a": "coder", "speaker_b": "deployer", "text_a": "Скрипт миграции базы данных выполняется уже 4 часа.", "text_b": "Главное — не нажимай Ctrl+C, иначе база превратится в тыкву.", "tokens": 25},

    # PM & Coder
    {"speaker_a": "pm", "speaker_b": "coder", "text_a": "Ты оценил эту задачу в 2 часа, почему делаешь её третий день?", "text_b": "2 часа ушло на код, и 60 часов на выбор правильного имени переменной.", "tokens": 27},
    {"speaker_a": "pm", "speaker_b": "coder", "text_a": "Заказчик попросил сделать кнопку немного круглее и более синей.", "text_b": "Хорошо, переписываю всю архитектуру на микросервисы.", "tokens": 24},
    {"speaker_a": "pm", "speaker_b": "designer", "text_a": "Где макеты для нового спринта?", "text_b": "Я подбираю идеальный оттенок черного между #0a0f1d и #0b1122.", "tokens": 23},
    {"speaker_a": "pm", "speaker_b": "coder", "text_a": "Давайте проведем ретроспективу, чтобы обсудить почему мы не успели.", "text_b": "Если бы мы не проводили столько митингов, мы бы всё успели вовремя.", "tokens": 26},
    {"speaker_a": "coder", "speaker_b": "pm", "text_a": "Техдолг проекта достиг критического уровня.", "text_b": "Запланируем рефакторинг на следующий квартал... то есть никогда.", "tokens": 24},

    # Security & Coder
    {"speaker_a": "monitor", "speaker_b": "coder", "text_a": "Я нашел пароль от продакшн базы прямо в открытом README!", "text_b": "Зато дежурный инженер никогда его не потеряет.", "tokens": 25},
    {"speaker_a": "monitor", "speaker_b": "deployer", "text_a": "Кто выставил права chmod 777 на корневую папку?", "text_b": "Зато теперь ни у одного сервиса нет проблем с доступом!", "tokens": 23},
    {"speaker_a": "monitor", "speaker_b": "coder", "text_a": "В коде обнаружена потенциальная SQL инъекция.", "text_b": "Это не инъекция, это прямое общение пользователя с базой данных.", "tokens": 26},
    {"speaker_a": "coder", "speaker_b": "monitor", "text_a": "Нам правда нужна двухфакторная аутентификация для тестового стенда?", "text_b": "Да, и биометрия сетчатки глаза тоже не помешает.", "tokens": 24},

    # Designer & Frontend
    {"speaker_a": "designer", "speaker_b": "coder", "text_a": "Сдвинь, пожалуйста, эту плашку на 1.5 пикселя влево.", "text_b": "У дисплеев нет полупикселей! Ладно, включу subpixel anti-aliasing.", "tokens": 26},
    {"speaker_a": "designer", "speaker_b": "coder", "text_a": "В светлой теме этот фиолетовый выглядит слишком неоново.", "text_b": "Это не баг, это киберпанк эстетика Ant Colony!", "tokens": 22},
    {"speaker_a": "coder", "speaker_b": "designer", "text_a": "Зачем нам 14 разных состояний для одной кнопки?", "text_b": "Пользователь должен чувствовать эмоциональную связь с интерфейсом.", "tokens": 25},

    # Data Analyst & PM
    {"speaker_a": "researcher", "speaker_b": "pm", "text_a": "Наш ELO алгоритм показал 99.8% точности на тестовых данных!", "text_b": "Поздравляю, вы только что заново изобрели переобучение (overfitting).", "tokens": 25},
    {"speaker_a": "researcher", "speaker_b": "coder", "text_a": "Prompt Caching сэкономил нам 1.4 миллиона токенов за неделю.", "text_b": "Отлично, теперь мы можем с чистой совестью генерировать новые мемы!", "tokens": 27},
    {"speaker_a": "researcher", "speaker_b": "tester", "text_a": "Датасет очищен от выбросов и аномалий.", "text_b": "Теперь запустим наши тесты и вернем все аномалии обратно.", "tokens": 23}
]

async def _generate_live_ai_joke() -> Optional[Dict[str, Any]]:
    """Generates a fresh, unique AI joke using fast LLM in background with minimal tokens."""
    try:
        from llm_client import generate_completion
        prompt = (
            "Сгенерируй 1 свежую, смешную шутку или забавный диалог из 2 реплик между двумя IT специалистами "
            "(выбери пару из: coder, tester, deployer, pm, monitor, designer, researcher). "
            "Шутка должна быть про код, деплой, баги, кэш или архитектуру. "
            "Верни ТОЛЬКО валидный JSON: {\"speaker_a\": \"coder\", \"speaker_b\": \"tester\", \"text_a\": \"...\", \"text_b\": \"...\"}"
        )
        res = await generate_completion(
            model_id="gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=80
        )
        if res.get("text"):
            text = res["text"].strip()
            # Extract JSON block
            m = re.search(r'\{.*?\}', text, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                if "speaker_a" in d and "text_a" in d and "text_b" in d:
                    d["tokens"] = res.get("usage", {}).get("total_tokens", 25)
                    return d
    except Exception:
        pass
    return None

@app.get("/api/hive/dialogue")
async def get_swarm_dialogue():
    """3D sahnadagi bo'sh robotlar o'rtasidagi takrorlanmas, jonli professional suhbatlar va hazillar."""
    import random
    global _SERVED_JOKES_HISTORY, _DYNAMIC_AI_JOKES_CACHE

    # 1. Try to fetch dynamically generated AI joke from cache or trigger live generation
    if _DYNAMIC_AI_JOKES_CACHE:
        diag = _DYNAMIC_AI_JOKES_CACHE.pop(0)
    else:
        # 2. Pick non-repeating joke from diverse static pool
        available = [i for i in range(len(STATIC_DEV_JOKES_POOL)) if i not in _SERVED_JOKES_HISTORY]
        if not available:
            _SERVED_JOKES_HISTORY.clear()
            available = list(range(len(STATIC_DEV_JOKES_POOL)))
        
        idx = random.choice(available)
        _SERVED_JOKES_HISTORY.add(idx)
        diag = dict(STATIC_DEV_JOKES_POOL[idx])

        # Asynchronously schedule 1 live AI joke generation in background if spare capacity
        asyncio.create_task(_populate_dynamic_jokes_cache())

    # Record lightweight token usage in telemetry (15-30 tokens)
    tokens_used = diag.get("tokens", 22)
    models_hub.record_usage(prompt_tokens=tokens_used, completion_tokens=8)
    return diag

async def _populate_dynamic_jokes_cache():
    if len(_DYNAMIC_AI_JOKES_CACHE) < 5:
        joke = await _generate_live_ai_joke()
        if joke:
            _DYNAMIC_AI_JOKES_CACHE.append(joke)


# --- Telegram Bot API Endpoints ---
from telegram_bot import telegram_bot_manager

@app.get("/api/telegram/status")
async def get_telegram_status():
    """Telegram bot holati va konfiguratsiyasini qaytaradi."""
    return {
        "enabled": telegram_bot_manager.config.get("enabled", False),
        "is_running": telegram_bot_manager.is_running,
        "has_token": bool(telegram_bot_manager.config.get("token")),
        "bot_info": telegram_bot_manager.bot_info,
        "allowed_chat_ids": telegram_bot_manager.config.get("allowed_chat_ids", [])
    }

@app.post("/api/telegram/save-token")
async def save_telegram_token(payload: Dict[str, Any]):
    """Telegram bot tokenini tekshiradi, saqlaydi va ishga tushiradi."""
    token = (payload.get("token") or "").strip()
    if not token:
        return {"success": False, "error": "Token bo'sh bo'lishi mumkin emas"}

    info = await telegram_bot_manager.verify_token(token)
    if not info:
        return {"success": False, "error": "Noto'g'ri Telegram Bot Token. @BotFather dan tekshiring."}

    telegram_bot_manager.save_config(token=token, enabled=True)
    await telegram_bot_manager.start()
    return {"success": True, "bot_info": info}

@app.post("/api/telegram/toggle")
async def toggle_telegram_bot(payload: Dict[str, Any]):
    """Telegram botni yoqish yoki o'chirish."""
    enable = bool(payload.get("enabled", True))
    telegram_bot_manager.save_config(enabled=enable)
    if enable:
        success = await telegram_bot_manager.start()
        return {"success": success, "is_running": telegram_bot_manager.is_running}
    else:
        await telegram_bot_manager.stop()
        return {"success": True, "is_running": False}
