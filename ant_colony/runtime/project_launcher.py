"""
Project Launcher — loyihalarni localhost'da avtomatik ishga tushiradi.

Loyiha turini tan olib (static HTML, Python Flask, Node.js, FastAPI) mos server
ishga tushiradi va foydalanuvchiga tayyor `http://localhost:PORT` linki qaytaradi.

Har bir chaqiruv:
  * Loyihada `index.html` bo'lsa → `python -m http.server` (static)
  * `main.py` va `flask`/`fastapi` bog'liqligi bo'lsa → uvicorn/flask run
  * `package.json` bo'lsa va `scripts.dev` bo'lsa → `npm run dev`
  * `app.py`/`server.py` FastAPI bilan → uvicorn

Xavfsiz port ajratish (8100-8199 oralig'i, bo'sh port topiladi).
Ishga tushirilgan jarayonlar `PROJECT_PROCESSES` dict'ida saqlanadi — foydalanuvchi
bir loyihani ikki marta yoqmasin, va to'xtatish endpointi orqali o'chirilsin.
"""
import os
import re
import time
import socket
import shutil
import signal
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


# Loyiha uchun ajratilgan portlar oralig'i
PORT_RANGE_START = 8100
PORT_RANGE_END = 8199

# Ishga tushirilgan jarayonlar reyestri.
# key = project_dir absolute path, value = {proc, port, url, started_at, kind}
_PROCESSES: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _find_free_port(start: int = PORT_RANGE_START, end: int = PORT_RANGE_END) -> int:
    """Berilgan oraliqda bo'sh portni topadi."""
    for p in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
                return p
        except OSError:
            continue
    raise RuntimeError(f"Bo'sh port topilmadi (oraliq {start}-{end})")


def _detect_project_kind(project_dir: Path) -> Dict[str, Any]:
    """
    Loyiha turini avtomatik tan oladi.
    Qaytaradi: {"kind": str, "entry": str|None, "confidence": float}
    """
    files = {f.name.lower() for f in project_dir.iterdir() if f.is_file()}

    # 1. Node.js / npm loyiha (React, Vue, Next.js)
    if "package.json" in files:
        try:
            import json
            pkg = json.loads((project_dir / "package.json").read_text(encoding="utf-8", errors="ignore"))
            scripts = pkg.get("scripts", {})
            if "dev" in scripts:
                return {"kind": "npm_dev", "entry": None, "confidence": 0.95}
            if "start" in scripts:
                return {"kind": "npm_start", "entry": None, "confidence": 0.9}
        except Exception:
            pass

    # 2. Python — FastAPI / Flask (app.py / server.py / main.py)
    for pyfile in ("app.py", "server.py", "main.py", "run.py"):
        if pyfile in files:
            try:
                content = (project_dir / pyfile).read_text(encoding="utf-8", errors="ignore")[:4000]
                if re.search(r"from\s+fastapi\s+import\s+FastAPI|FastAPI\(\)", content):
                    # ASGI variable nomini topamiz
                    var_match = re.search(r"^(\w+)\s*=\s*FastAPI\(", content, re.MULTILINE)
                    var_name = var_match.group(1) if var_match else "app"
                    return {"kind": "fastapi", "entry": pyfile, "asgi_var": var_name, "confidence": 0.95}
                if re.search(r"from\s+flask\s+import\s+Flask|Flask\(__name__\)", content):
                    return {"kind": "flask", "entry": pyfile, "confidence": 0.9}
                if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", content):
                    return {"kind": "python_main", "entry": pyfile, "confidence": 0.6}
            except Exception:
                continue

    # 3. Static HTML (index.html mavjud)
    if "index.html" in files:
        return {"kind": "static", "entry": "index.html", "confidence": 0.85}

    # 4. Go binary (main.go)
    if "main.go" in files:
        return {"kind": "go", "entry": "main.go", "confidence": 0.8}

    # 5. PHP (index.php)
    if "index.php" in files:
        return {"kind": "php", "entry": "index.php", "confidence": 0.75}

    return {"kind": "unknown", "entry": None, "confidence": 0.0}


def _build_command(kind: str, entry: Optional[str], asgi_var: str, port: int, project_dir: Path) -> Optional[List[str]]:
    """Loyiha turiga qarab shell buyruqni yasaydi."""
    py = shutil.which("python3") or shutil.which("python") or "python3"

    if kind == "static":
        return [py, "-m", "http.server", str(port), "--bind", "127.0.0.1"]

    if kind == "fastapi":
        # entry: "app.py" → module "app", ASGI var "app" default
        module = Path(entry).stem
        return [py, "-m", "uvicorn", f"{module}:{asgi_var}",
                "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]

    if kind == "flask":
        env_cmd = [
            py, "-c",
            f"import os; os.environ['FLASK_APP']='{entry}'; os.environ['FLASK_RUN_PORT']='{port}';"
            f" from flask.cli import main; main()"
        ]
        # Sodda usul: flask run
        flask = shutil.which("flask")
        if flask:
            return [flask, "--app", entry, "run", "--host", "127.0.0.1", "--port", str(port)]
        return None

    if kind == "python_main":
        return [py, entry]

    if kind == "npm_dev":
        npm = shutil.which("npm")
        if not npm:
            return None
        return [npm, "run", "dev", "--", "--port", str(port), "--host", "127.0.0.1"]

    if kind == "npm_start":
        npm = shutil.which("npm")
        if not npm:
            return None
        return [npm, "start"]

    if kind == "php":
        php = shutil.which("php")
        if not php:
            return None
        return [php, "-S", f"127.0.0.1:{port}", "-t", str(project_dir)]

    if kind == "go":
        go = shutil.which("go")
        if not go:
            return None
        return [go, "run", entry]

    return None


def launch_project(project_dir: str | Path) -> Dict[str, Any]:
    """
    Loyihani localhost'da ishga tushiradi. Agar allaqachon ishlab tursa —
    o'sha URL qaytariladi.
    """
    project_dir = Path(project_dir).resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        return {"success": False, "error": f"Papka topilmadi: {project_dir}"}

    key = str(project_dir)

    with _LOCK:
        existing = _PROCESSES.get(key)
        if existing and existing["proc"].poll() is None:
            return {
                "success": True,
                "already_running": True,
                "url": existing["url"],
                "port": existing["port"],
                "kind": existing["kind"],
                "project_dir": key,
                "started_at": existing["started_at"],
            }
        elif existing:
            # Jarayon o'lgan — reyestrdan olib tashlaymiz
            _PROCESSES.pop(key, None)

        detect = _detect_project_kind(project_dir)
        kind = detect["kind"]
        if kind == "unknown":
            return {
                "success": False,
                "error": "Loyiha turi tan olinmadi (index.html, main.py, package.json, index.php topilmadi)",
                "project_dir": key,
            }

        try:
            port = _find_free_port()
        except Exception as e:
            return {"success": False, "error": str(e), "project_dir": key}

        cmd = _build_command(kind, detect.get("entry"), detect.get("asgi_var", "app"), port, project_dir)
        if not cmd:
            return {
                "success": False,
                "error": f"'{kind}' turini ishga tushiruvchi asbob topilmadi (npm/php/go o'rnatilmagan bo'lishi mumkin)",
                "project_dir": key, "kind": kind,
            }

        try:
            # Log fayl — jarayon chiqishi shu yerga yoziladi
            log_dir = project_dir / ".ant_colony_run"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "server.log"
            proc = subprocess.Popen(
                cmd,
                cwd=str(project_dir),
                stdout=log_file.open("wb"),
                stderr=subprocess.STDOUT,
                # Jarayon guruhini o'zi ochsin — barcha bola jarayonlarni birga to'xtatish uchun
                start_new_session=True,
            )
        except Exception as e:
            return {"success": False, "error": f"Ishga tushirib bo'lmadi: {e}", "project_dir": key}

        # Portning ochilishini kutamiz (max 4s)
        deadline = time.time() + 4.0
        port_open = False
        while time.time() < deadline:
            if proc.poll() is not None:
                # Jarayon darhol tugadi — xato bor
                break
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        port_open = True
                        break
            except Exception:
                pass
            time.sleep(0.2)

        # `npm run dev` uchun port kechroq ochilishi mumkin — jarayon tirik bo'lsa OK deb hisoblaymiz
        alive = proc.poll() is None
        if not alive:
            # Log'dan sabab olamiz
            try:
                error_tail = log_file.read_text(encoding="utf-8", errors="ignore")[-800:]
            except Exception:
                error_tail = "log yo'q"
            return {
                "success": False,
                "error": f"Jarayon ishga tushmadi (exit {proc.poll()}). Log:\n{error_tail}",
                "project_dir": key, "kind": kind,
            }

        url = f"http://127.0.0.1:{port}"
        entry = {
            "proc": proc, "port": port, "url": url,
            "started_at": time.time(), "kind": kind,
            "cmd": " ".join(cmd), "log_file": str(log_file),
        }
        _PROCESSES[key] = entry

        return {
            "success": True,
            "url": url, "port": port, "kind": kind,
            "port_confirmed": port_open,
            "project_dir": key,
            "started_at": entry["started_at"],
            "message": f"Loyiha ishga tushdi: {url}" + ("" if port_open else " (port hali ochilyapti, brauzerni oching)"),
        }


def stop_project(project_dir: str | Path) -> Dict[str, Any]:
    """Loyiha jarayonini to'xtatadi."""
    key = str(Path(project_dir).resolve())
    with _LOCK:
        entry = _PROCESSES.get(key)
        if not entry:
            return {"success": False, "error": "Ishlab turgan loyiha topilmadi", "project_dir": key}
        proc = entry["proc"]
        if proc.poll() is None:
            try:
                # Butun jarayon guruhini to'xtatamiz (npm shell + node bola)
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            # Kutamiz
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
        _PROCESSES.pop(key, None)
        return {"success": True, "project_dir": key, "message": "Loyiha to'xtatildi"}


def list_running() -> Dict[str, Any]:
    """Hozir ishlab turgan loyihalar ro'yxati."""
    with _LOCK:
        rows = []
        dead = []
        for key, e in _PROCESSES.items():
            alive = e["proc"].poll() is None
            if not alive:
                dead.append(key)
                continue
            rows.append({
                "project_dir": key, "url": e["url"], "port": e["port"],
                "kind": e["kind"], "started_at": e["started_at"],
                "uptime_s": round(time.time() - e["started_at"], 1),
            })
        for k in dead:
            _PROCESSES.pop(k, None)
        return {"count": len(rows), "running": rows}


def stop_all() -> Dict[str, Any]:
    """Barcha loyihalarni to'xtatadi (server tugaganda ishlatiladi)."""
    with _LOCK:
        keys = list(_PROCESSES.keys())
    for k in keys:
        stop_project(k)
    return {"success": True, "stopped": len(keys)}
