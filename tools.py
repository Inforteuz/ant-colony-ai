"""
Platform Tools: Real Terminal Execution, Desktop 04_Loyihalar Directory Files, Python Interpreter, and Memory.

Har bir asbob JSON Schema bilan e'lon qilinadi — shu sxemalar ham LLM'ga native
function-calling uchun yuboriladi, ham prompt matnidagi qo'llanmani generatsiya qiladi.
Shu tarzda prompt va haqiqiy asboblar hech qachon bir-biridan uzilib qolmaydi.
"""
import os
import re
import sys
import ast
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from config import BASE_DIR, WORKSPACE_DIR, PROJECTS_BASE_DIR

# Active Project Directory (Defaults to 04_Loyihalar)
CURRENT_PROJECT_DIR: Path = PROJECTS_BASE_DIR

# --- Live Event Emitter (Real-time file tree & terminal streaming) ---
# Orkestratsiya davomida `server.py` bu erga callback o'rnatadi va har bir
# fayl yaratilishi/tahrirlanishi va terminal chiqishi jonli SSE stream'ga
# yuboriladi. Callback yo'q bo'lsa, tools jimgina ishlaydi.
_EVENT_EMITTER: Optional[Callable[[Dict[str, Any]], None]] = None


def set_event_emitter(cb: Optional[Callable[[Dict[str, Any]], None]]):
    """Live event callback o'rnatadi. `None` yuborsangiz — o'chiriladi."""
    global _EVENT_EMITTER
    _EVENT_EMITTER = cb


def _emit(event: Dict[str, Any]):
    """Callback o'rnatilgan bo'lsa event yuboradi. Xatolarga chidamli."""
    cb = _EVENT_EMITTER
    if not cb:
        return
    try:
        cb(event)
    except Exception:
        pass

# Chiqishlar LLM kontekstini to'ldirib yubormasligi uchun kesish chegarasi.
MAX_OUTPUT_CHARS = 6000

# Fayl daraxtini aylanib o'tish chegaralari.
# Foydalanuvchining loyihalar papkasi 600 mingdan ortiq fayl va o'nlab GB bo'lishi
# mumkin — chegarasiz `rglob("*")` butun daraxtni aylanib, so'rovni muzlatib qo'yadi.
MAX_WALK_FILES = 400
MAX_WALK_DEPTH = 6
IGNORED_DIR_NAMES = {
    "node_modules", "__pycache__", ".git", ".svn", ".hg", "venv", ".venv",
    "env", ".env.d", "dist", "build", ".next", ".nuxt", "target", ".cache",
    ".idea", ".vscode", "vendor", "Pods", ".gradle", ".tox", "site-packages",
    ".pytest_cache", ".mypy_cache", ".DS_Store", "coverage", ".terraform",
}


def _skip_entry(name: str) -> bool:
    return name.startswith(".") or name.startswith("_temp_") or name in IGNORED_DIR_NAMES


def walk_project_files(
    root: Path,
    *,
    limit: int = MAX_WALK_FILES,
    max_depth: int = MAX_WALK_DEPTH,
    include_dirs: bool = False,
) -> tuple[List[tuple[Path, str]], bool]:
    """
    Papkani chegaralangan tarzda aylanib o'tadi: (yo'l, nisbiy_yo'l) juftliklari
    va chegaraga urilgan-urilmagani. `os.scandir` ishlatiladi — `rglob` dan tezroq
    va og'ir papkalarni ochmasdan o'tkazib yuborish imkonini beradi.
    """
    results: List[tuple[Path, str]] = []
    truncated = False
    try:
        root = root.resolve()
    except Exception:
        return results, truncated
    if not root.exists() or not root.is_dir():
        return results, truncated

    stack: List[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if len(results) >= limit:
                        return results, True
                    if _skip_entry(entry.name):
                        continue
                    path = Path(entry.path)
                    try:
                        rel = path.relative_to(root).as_posix()
                    except Exception:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if include_dirs:
                            results.append((path, rel))
                        if depth + 1 <= max_depth:
                            stack.append((path, depth + 1))
                    elif entry.is_file(follow_symlinks=False):
                        results.append((path, rel))
        except (PermissionError, OSError):
            continue
    return results, truncated

# Qaytarib bo'lmaydigan/xavfli buyruqlar — agent tasodifan tizimni buzmasligi uchun.
# Har bir naqsh nima uchun bloklangani izohlangan.
BLOCKED_COMMAND_PATTERNS = [
    # Fayllarni buzuvchi
    (r"\brm\s+(-[a-zA-Z]*\s+)*/(\s|$)",              "rm -rf /"),
    (r"\brm\s+(-[a-zA-Z]*\s+)*~(/\s*)?(\s|$)",        "rm -rf ~"),
    (r":\(\)\s*\{.*\};\s*:",                          "fork bomb"),
    (r"\bmkfs\b",                                     "diskni formatlash"),
    (r"\bdd\s+if=.*of=/dev/",                         "diskga to'g'ridan-to'g'ri yozish"),
    (r">\s*/dev/sd[a-z]",                             "diskka redirect"),
    # Tizim boshqaruvi
    (r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b", "tizimni o'chirish"),
    (r"\bsudo\b",                                     "sudo bilan huquq ko'tarish"),
    (r"\bsu\s+-|\bsu\s+root\b",                       "root'ga o'tish"),
    (r"\bchmod\s+(-[a-zA-Z]*\s+)*777\s+/(\s|$)",       "chmod 777 /"),
    (r"\bchown\s+-R\s+.+\s+/(\s|$)",                   "chown / root"),
    # Tarmoq → shell pipe (RCE naqshi)
    (r"\bcurl\s+[^|]*\|\s*(bash|sh|zsh|python|perl|ruby|node)\b",
        "curl | shell (masofadan kod bajarish)"),
    (r"\bwget\s+[^|]*\|\s*(bash|sh|zsh|python|perl|ruby|node)\b",
        "wget | shell (masofadan kod bajarish)"),
    (r"\bcurl\s+[^|]*\|\s*(bash|sh)\s*-",              "curl | sh -"),
    # Reverse / bind shell
    (r"\bnc(at)?\s+.*-e\s+/?(bin/)?(bash|sh|zsh)\b",   "reverse shell (nc -e)"),
    (r"\bbash\s+-i\s+>&?\s*/dev/tcp/",                 "bash -i /dev/tcp reverse shell"),
    (r"\bpython\s+-c\s+.*socket\.socket.*connect",     "python socket reverse shell"),
    (r"/dev/tcp/\d+\.\d+\.\d+\.\d+/",                  "TCP socket exfil"),
    # Maxfiy kalit exfiltratsiyasi
    (r"\bcat\s+.*~/\.ssh/id_(rsa|ed25519|ecdsa|dsa)\b",         "SSH shaxsiy kaliti"),
    (r"\bcat\s+.*~/\.aws/credentials\b",                        "AWS credentials"),
    (r"\bcat\s+.*~/\.config/gcloud/.*\.json\b",                 "GCP credentials"),
    (r"\bcat\s+.*\.env(\s|$)",                                  "env fayli (maxfiylar bo'lishi mumkin)"),
    (r"\benv\s*\|\s*(curl|wget|nc)\b",                          "env → tarmoq"),
    # Boshqa xavfli
    (r"\b(kill|pkill|killall)\s+-9\s+-1\b",           "barcha jarayonlarni o'ldirish"),
    (r"\bshred\b.*\s+/",                              "diskni tozalash"),
    (r"\bfdisk\b.*\s+/dev/",                          "diskni qayta bo'lish"),
]

# Fayl daraxti chegarasidan tashqariga chiqishga urinish (murakkab holatlar,
# global chegarani xavfsiz saqlab qolish uchun).
_PATH_ESCAPE_PATTERNS = [
    r"\bcd\s+/(\s|$|;)",             # cd /
    r"\bcd\s+~(\s|$|;)",             # cd ~
    r"\bcd\s+\.\./\.\./\.\.",         # ../../..
]


def set_active_project_dir(path: Path):
    global CURRENT_PROJECT_DIR
    CURRENT_PROJECT_DIR = path
    try:
        CURRENT_PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def get_active_project_dir() -> Path:
    return CURRENT_PROJECT_DIR


def _clip(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Uzun chiqishni kesib, agentga nima kesilganini aytadi."""
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.7)]
    tail = text[-int(limit * 0.25):]
    return f"{head}\n\n... [{len(text) - limit} belgi kesildi] ...\n\n{tail}"


def _normalize_relative_path(raw_path: str, root: Path) -> str:
    """
    LLM tomonidan yuborilgan har qanday to'liq, nisbiy yoki takroriy yo'lni
    loyiha papkasiga nisbatan toza nisbiy yo'lga aylantiradi.
    O'z-o'ziga ichma-ich papka ochish (`planetarium/planetarium/index.html`) muammosini oldini oladi.
    """
    raw = (raw_path or "").strip().replace("\\", "/").strip()
    if not raw:
        return ""

    # 1. Agar to'liq absolut yo'l bo'lsa
    p = Path(raw)
    if p.is_absolute():
        try:
            return p.relative_to(root).as_posix()
        except Exception:
            try:
                rel = p.relative_to(PROJECTS_BASE_DIR.resolve()).as_posix()
                if rel.startswith(root.name + "/"):
                    return rel[len(root.name) + 1:]
                elif rel == root.name:
                    return p.name
                return rel
            except Exception:
                return p.name

    raw = raw.lstrip("/")

    # 2. Agar absolut yo'l boshidagi slashsiz berilgan bo'lsa
    root_str = str(root.resolve()).lstrip("/")
    if raw.startswith(root_str + "/"):
        raw = raw[len(root_str) + 1:]

    # 3. Agar `04_Loyihalar/` prefiksi bo'lsa
    if "04_Loyihalar/" in raw:
        after = raw.split("04_Loyihalar/", 1)[1]
        if after.startswith(root.name + "/"):
            raw = after[len(root.name) + 1:]
        else:
            raw = after

    # 4. Agar papka nomi boshida takrorlansa (masalan `planetarium-canvas-anim/index.html`)
    while root.name and raw.startswith(root.name + "/"):
        raw = raw[len(root.name) + 1:]

    return raw.strip("/")


def _safe_target(relative_path: str, base: Optional[Path] = None) -> Path:
    """
    Nisbiy yo'lni loyiha papkasi ichida xavfsiz hal qiladi.
    Papkalar ichidagi fayllarga ruxsat beradi (`src/main.py`), lekin loyiha
    papkasidan tashqariga chiqishni yoki o'z-o'ziga ichma-ich papka ochishni bloklaydi.
    """
    root = (base or CURRENT_PROJECT_DIR).resolve()
    norm = _normalize_relative_path(relative_path, root)
    if not norm:
        raise ValueError("Fayl nomi bo'sh")
    candidate = (root / norm).resolve()
    if candidate != root and root not in candidate.parents:
        # Yo'l tashqariga chiqmoqchi — faqat fayl nomini olib, ildizga joylaymiz.
        candidate = (root / Path(norm).name).resolve()
    return candidate


def _check_command_safety(command: str) -> Optional[str]:
    """Buyruqni bloklash naqshlariga qarab tekshiradi. Bloklangan bo'lsa sabab qaytadi."""
    if not command or not command.strip():
        return "Buyruq bo'sh"
    if len(command) > 8000:
        return "Buyruq juda uzun (>8000 belgi) — RCE gumoni"
    for pattern, reason in BLOCKED_COMMAND_PATTERNS:
        if re.search(pattern, command):
            return f"Bloklandi: {reason}"
    return None


# --- Resource limits (Unix) ---
def _apply_sandbox_limits():
    """
    Subprocess ichida resource cheklovlarini o'rnatadi. `preexec_fn` sifatida
    ishlatiladi — fork'dan keyin, exec'dan oldin ishlaydi. Windows'da ishlamaydi.
    """
    try:
        import resource
    except ImportError:
        return
    # Yangi jarayon guruhi — timeout'da butun daraxtni o'chirish uchun.
    try:
        os.setsid()
    except OSError:
        pass
    limits = [
        # CPU vaqti (soft/hard) — cheksiz sikldan himoya. 120s soft, 180s hard.
        (resource.RLIMIT_CPU, (120, 180)),
        # Umumiy fayl hajmi (yaratish) — 200MB
        (resource.RLIMIT_FSIZE, (200 * 1024 * 1024, 200 * 1024 * 1024)),
        # Ochiq fayl deskriptorlari
        (resource.RLIMIT_NOFILE, (1024, 2048)),
    ]
    # Xotira: RLIMIT_AS macOS'da ishlamaydi (ishonchsiz), Linuxda esa ishlaydi.
    if sys.platform.startswith("linux"):
        limits.append((resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 3 * 1024 * 1024 * 1024)))  # 2GB soft
        # Jarayonlar soni — fork bombdan himoya
        limits.append((resource.RLIMIT_NPROC, (256, 512)))
    for res_id, pair in limits:
        try:
            resource.setrlimit(res_id, pair)
        except (ValueError, OSError):
            continue


# --- Secret redaction ---
_SECRET_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),           "sk-***REDACTED***"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),  "xox*-***REDACTED***"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),          "ghp_***REDACTED***"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"),              "AKIA***REDACTED***"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),        "AIza***REDACTED***"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
                                                        "eyJ***JWT_REDACTED***"),
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", re.DOTALL),
                                                        "-----REDACTED_PRIVATE_KEY-----"),
]


def _redact_secrets(text: str) -> str:
    """Ochiq maxfiylarni chiqishdan tozalaydi — LLM kontekstiga sizib kirmasin."""
    if not text:
        return text
    for pat, sub in _SECRET_PATTERNS:
        text = pat.sub(sub, text)
    return text


def _kill_process_tree(proc: subprocess.Popen):
    """
    Popen jarayoni va uning butun jarayon guruhini o'ldiradi.
    `preexec_fn=setsid` bilan yaratilgan bo'lsa, `killpg` yordamida bolalar ham
    to'xtatiladi. Aks holda oddiy `kill()` ga tushamiz.
    """
    if proc.poll() is not None:
        return
    if os.name == "posix":
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, 15)  # SIGTERM
            # Yumshoq to'xtash imkoniyati
            try:
                proc.wait(timeout=1.5)
                return
            except subprocess.TimeoutExpired:
                pass
            os.killpg(pgid, 9)   # SIGKILL
            return
        except (ProcessLookupError, PermissionError, OSError):
            pass
    try:
        proc.kill()
    except Exception:
        pass


# --- Audit log ---
_AUDIT_LOG_PATH = BASE_DIR / "shell_audit.log"


def _audit_log(command: str, cwd: str, result: Dict[str, Any]):
    """Har bir bajarilgan (yoki bloklangan) shell buyrug'ini fayldagi jurnalga yozadi."""
    try:
        entry = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cwd": cwd,
            "command": command[:500],
            "success": result.get("success"),
            "returncode": result.get("returncode"),
            "blocked": result.get("blocked", False),
            "duration_ms": result.get("duration_ms"),
        }
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # audit fail — asosiy oqimni to'xtatmaymiz


def run_shell_command(command: str, cwd: Optional[str] = None, timeout: int = 60) -> Dict[str, Any]:
    """
    Execute a shell command with full system access.
    Runs in the active Desktop project directory by default.
    Terminal chiqishi live event emitter orqali qatorma-qator jonli uzatiladi.
    """
    t0 = time.time()
    exec_id = f"exec_{int(t0 * 1000)}"

    blocked = _check_command_safety(command)
    if blocked:
        _emit({
            "type": "terminal_stream", "exec_id": exec_id, "phase": "blocked",
            "command": command, "line": blocked, "stream": "stderr",
            "timestamp": time.time(),
        })
        blocked_result = {
            "success": False, "command": command, "stdout": "",
            "stderr": blocked, "returncode": -1,
            "cwd": str(CURRENT_PROJECT_DIR), "duration_ms": 0, "blocked": True
        }
        _audit_log(command, str(CURRENT_PROJECT_DIR), blocked_result)
        return blocked_result

    work_dir = Path(cwd) if cwd else CURRENT_PROJECT_DIR
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        work_dir = WORKSPACE_DIR

    _emit({
        "type": "terminal_stream", "exec_id": exec_id, "phase": "start",
        "command": command, "cwd": str(work_dir), "timestamp": time.time(),
    })

    stdout_buf: List[str] = []
    stderr_buf: List[str] = []
    proc: Optional[subprocess.Popen] = None
    timeout_hit = False

    try:
        import threading
        import queue as _queue

        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            preexec_fn=_apply_sandbox_limits if os.name == "posix" else None,
        )

        # Har bir oqim uchun alohida thread — Popen'da parallel o'qimasak, buffer
        # to'lib blocklanadi. Threadlar chiziqlarni umumiy queue'ga qo'yadi.
        line_q: "_queue.Queue[tuple[str, Optional[str]]]" = _queue.Queue()

        def pump(stream, kind: str):
            try:
                for raw in iter(stream.readline, ""):
                    if not raw:
                        break
                    line_q.put((kind, raw.rstrip("\n")))
            finally:
                line_q.put((kind, None))  # sentinel: shu oqim tugadi
                try:
                    stream.close()
                except Exception:
                    pass

        t_out = threading.Thread(target=pump, args=(proc.stdout, "stdout"), daemon=True)
        t_err = threading.Thread(target=pump, args=(proc.stderr, "stderr"), daemon=True)
        t_out.start(); t_err.start()

        wait_deadline = t0 + max(5, min(int(timeout), 300))
        streams_open = 2

        while streams_open > 0:
            remaining = wait_deadline - time.time()
            if remaining <= 0:
                timeout_hit = True
                _kill_process_tree(proc)
                break
            try:
                kind, line = line_q.get(timeout=min(0.5, remaining))
            except _queue.Empty:
                if proc.poll() is not None and line_q.empty():
                    # Jarayon tugadi va yana chiziqlar yo'q — chiqamiz
                    break
                continue

            if line is None:
                streams_open -= 1
                continue

            if kind == "stdout":
                stdout_buf.append(line)
            else:
                stderr_buf.append(line)

            _emit({
                "type": "terminal_stream", "exec_id": exec_id, "phase": "line",
                "line": line, "stream": kind, "timestamp": time.time(),
            })

        # Jarayon hali tirik bo'lsa — kutamiz, keyin butun daraxtni o'ldiramiz
        try:
            returncode = proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            timeout_hit = True
            _kill_process_tree(proc)
            returncode = -1

        duration_ms = round((time.time() - t0) * 1000)
        stdout_txt = "\n".join(stdout_buf).strip()
        stderr_txt = "\n".join(stderr_buf).strip()

        if timeout_hit:
            tail = f"Terminal buyrug'i vaqti tugadi (>{timeout}s). Uzoq ishlaydigan buyruqlarni fonda ishga tushiring yoki qisqartiring."
            stderr_txt = (stderr_txt + "\n" + tail).strip() if stderr_txt else tail
            _emit({
                "type": "terminal_stream", "exec_id": exec_id, "phase": "timeout",
                "line": tail, "stream": "stderr", "timestamp": time.time(),
            })

        _emit({
            "type": "terminal_stream", "exec_id": exec_id, "phase": "end",
            "returncode": returncode, "duration_ms": duration_ms,
            "success": returncode == 0 and not timeout_hit, "timestamp": time.time(),
        })

        result = {
            "success": returncode == 0 and not timeout_hit,
            "command": command,
            "stdout": _clip(_redact_secrets(stdout_txt)),
            "stderr": _clip(_redact_secrets(stderr_txt), 2500),
            "returncode": returncode,
            "cwd": str(work_dir),
            "duration_ms": duration_ms,
            "exec_id": exec_id,
        }
        _audit_log(command, str(work_dir), result)
        return result
    except Exception as e:
        _emit({
            "type": "terminal_stream", "exec_id": exec_id, "phase": "error",
            "line": str(e), "stream": "stderr", "timestamp": time.time(),
        })
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
        return {
            "success": False,
            "command": command,
            "stdout": "\n".join(stdout_buf).strip(),
            "stderr": str(e),
            "returncode": -1,
            "cwd": str(work_dir),
            "duration_ms": round((time.time() - t0) * 1000),
            "exec_id": exec_id,
        }


def execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code in the active project directory and capture stdout/stderr."""
    t0 = time.time()
    work_dir = CURRENT_PROJECT_DIR if CURRENT_PROJECT_DIR.exists() else WORKSPACE_DIR

    # Sintaksisni oldindan tekshirish — API chaqirig'ini behuda sarflamaslik uchun.
    try:
        ast.parse(code)
    except SyntaxError as e:
        return {
            "success": False, "stdout": "",
            "stderr": f"SyntaxError (kod ishga tushirilmadi): {e.msg} — {e.lineno}-qator",
            "returncode": -1, "duration_ms": 0
        }

    temp_file = work_dir / f"_temp_run_{int(time.time() * 1000)}.py"
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
        temp_file.write_text(code, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(temp_file)],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=max(5, min(int(timeout), 120))
        )
        return {
            "success": result.returncode == 0,
            "stdout": _clip(result.stdout.strip()),
            "stderr": _clip(result.stderr.strip(), 2500),
            "returncode": result.returncode,
            "duration_ms": round((time.time() - t0) * 1000)
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "stdout": "",
            "stderr": f"Python kodi bajarilish vaqti tugadi (>{timeout}s)",
            "returncode": -1, "duration_ms": round((time.time() - t0) * 1000)
        }
    except Exception as e:
        return {
            "success": False, "stdout": "", "stderr": str(e),
            "returncode": -1, "duration_ms": round((time.time() - t0) * 1000)
        }
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def calculate(expression: str) -> Dict[str, Any]:
    """Safely evaluate mathematical expressions."""
    try:
        allowed: Dict[str, Any] = {"__builtins__": {}}
        import math
        allowed.update({k: getattr(math, k) for k in dir(math) if not k.startswith("_")})
        allowed.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
        res = eval(expression, allowed, {})  # noqa: S307 — cheklangan nomlar maydoni
        return {"success": True, "expression": expression, "result": res}
    except Exception as e:
        return {"success": False, "expression": expression, "error": str(e)}


def write_file(filename: str, content: str) -> Dict[str, Any]:
    """
    Create or overwrite a file in the active project folder.
    Papka ichidagi yo'llar qo'llanadi: `src/utils/helpers.py`.
    """
    try:
        target = _safe_target(filename)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    rel = None
    try:
        rel = target.relative_to(CURRENT_PROJECT_DIR.resolve()).as_posix()
    except Exception:
        rel = target.name

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except Exception as e:
        return {"success": False, "filename": rel, "error": f"Faylni yozib bo'lmadi: {e}"}

    # Ishchi muhitga nusxa (UI fayllar ro'yxati uchun).
    ws_path = None
    try:
        ws_target = WORKSPACE_DIR / rel
        ws_target.parent.mkdir(parents=True, exist_ok=True)
        ws_target.write_text(content, encoding="utf-8")
        ws_path = str(ws_target)
    except Exception:
        pass

    # Python fayllarni darhol sintaksis bo'yicha tekshiramiz — agent xatoni
    # keyingi qadamda emas, shu zahoti ko'radi.
    syntax_note = None
    if rel.endswith(".py"):
        try:
            ast.parse(content)
            syntax_note = "Python sintaksisi to'g'ri"
        except SyntaxError as e:
            syntax_note = f"OGOHLANTIRISH — SyntaxError {e.lineno}-qatorda: {e.msg}"

    size_bytes = len(content.encode("utf-8"))
    line_count = content.count("\n") + 1

    _emit({
        "type": "fs_change",
        "op": "write",
        "filename": rel,
        "path": str(target),
        "size_bytes": size_bytes,
        "lines": line_count,
        "timestamp": time.time(),
    })

    return {
        "success": True,
        "filename": rel,
        "path": str(target),
        "workspace_path": ws_path,
        "size_bytes": size_bytes,
        "lines": line_count,
        "syntax_check": syntax_note,
        "message": f"Fayl yozildi: {target}"
    }


def edit_file(filename: str, old_text: str, new_text: str) -> Dict[str, Any]:
    """
    Faylning bir qismini almashtiradi — butun faylni qayta yozmasdan.
    Katta fayllarda tokenni sezilarli tejaydi.
    """
    try:
        target = _safe_target(filename)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if not target.exists() or not target.is_file():
        return {"success": False, "error": f"Fayl topilmadi: {filename}. Avval `write_file` bilan yarating."}

    try:
        content = target.read_text(encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Faylni o'qib bo'lmadi: {e}"}

    occurrences = content.count(old_text)
    if occurrences == 0:
        return {
            "success": False,
            "error": "`old_text` faylda topilmadi. Avval `read_file` bilan aniq matnni oling.",
            "filename": filename
        }
    if occurrences > 1:
        return {
            "success": False,
            "error": f"`old_text` {occurrences} marta uchraydi — noaniq. Ko'proq kontekst qo'shib takrorlang.",
            "filename": filename
        }

    updated = content.replace(old_text, new_text, 1)
    return write_file(filename, updated)


def _outline_python(content: str) -> str:
    """Python fayldan class va funksiya sarlavhalarini ajratadi (LLM'ga arzon xulosa)."""
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return f"# (parsing xatosi: {e.msg} on line {e.lineno})"
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = ", ".join(a.arg for a in node.args.args)
            lines.append(f"def {node.name}({args})  # line {node.lineno}")
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(getattr(b, "id", getattr(b, "attr", "?")) for b in node.bases)
            lines.append(f"class {node.name}({bases})  # line {node.lineno}")
    return "\n".join(lines) or "# (bo'sh yoki faqat imports)"


_JS_OUTLINE_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z_$][\w$]*)|class\s+([A-Za-z_$][\w$]*)|const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(?[^=]*=>)",
    re.MULTILINE,
)


def _outline_js(content: str) -> str:
    lines = []
    for m in _JS_OUTLINE_RE.finditer(content):
        name = m.group(1) or m.group(2) or m.group(3)
        line_no = content[: m.start()].count("\n") + 1
        kind = "class" if m.group(2) else "function"
        lines.append(f"{kind} {name}  // line {line_no}")
    return "\n".join(lines) or "// (top-level e'lonlar topilmadi)"


def read_file(filename: str, mode: str = "full") -> Dict[str, Any]:
    """
    Faylni o'qiydi. `mode`:
      * `full` — mazmun (12000 belgigacha kesiladi).
      * `outline` — faqat class/funksiya sarlavhalari (Python va JS/TS uchun).
        Katta fayllarda tokenlarni 10-20x tejaydi; agent kerak bo'lsa keyin
        `full` bilan qayta o'qiydi.
      * `range:START-END` — faqat berilgan qatorlar oralig'i (1-indeksli, inclusive).
    """
    raw = (filename or "").strip().replace("\\", "/").lstrip("/")
    if not raw:
        return {"success": False, "error": "Fayl nomi bo'sh"}

    target_name = Path(raw).name
    candidates: List[Path] = []

    # 1. To'g'ridan-to'g'ri yo'l bo'yicha (eng tez yo'l).
    for base in (CURRENT_PROJECT_DIR, PROJECTS_BASE_DIR, WORKSPACE_DIR):
        try:
            candidates.append(_safe_target(raw, base))
        except Exception:
            pass

    # 2. Topilmasa — faqat nom bo'yicha izlash, lekin CHEGARALANGAN tarzda.
    for base in (CURRENT_PROJECT_DIR, WORKSPACE_DIR):
        if not base.exists():
            continue
        found, _ = walk_project_files(base, limit=MAX_WALK_FILES)
        candidates.extend(p for p, rel in found if p.name == target_name)

    for path in candidates:
        try:
            if not (path.exists() and path.is_file()):
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            size_bytes = len(content.encode("utf-8"))
            total_lines = content.count("\n") + 1

            payload: Dict[str, Any] = {
                "success": True,
                "filename": path.name,
                "path": str(path),
                "size_bytes": size_bytes,
                "lines": total_lines,
                "mode": mode,
            }

            m = (mode or "full").strip().lower()
            if m == "outline":
                ext = path.suffix.lower()
                if ext == ".py":
                    outline = _outline_python(content)
                elif ext in (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"):
                    outline = _outline_js(content)
                else:
                    outline = f"# outline faqat .py/.js/.ts uchun qo'llanadi. Faylni `mode='full'` bilan o'qing."
                payload["outline"] = outline
                payload["content"] = ""
                return payload

            if m.startswith("range:"):
                try:
                    a, b = m.split(":", 1)[1].split("-", 1)
                    start = max(1, int(a))
                    end = max(start, int(b))
                    lines = content.splitlines()
                    slice_ = "\n".join(lines[start - 1 : end])
                    payload["content"] = _clip(slice_, 12000)
                    payload["range"] = f"{start}-{min(end, total_lines)}"
                    return payload
                except Exception:
                    pass  # noto'g'ri format — full rejimga tushamiz

            payload["content"] = _clip(content, 12000)
            return payload
        except Exception:
            continue

    return {"success": False, "error": f"Fayl topilmadi: {raw}", "filename": raw}


# --- Smart file relevance ranker ---

# Kalit so'zlarni fayllarga bog'lash — vazifa "python API" desa .py va api/ katalogi
# ustunlik oladi, "3D animatsiya" desa .js/.html va three fayli ustunlik oladi.
_EXT_WEIGHTS_BY_KEYWORD = {
    "python":     {".py": 6.0, ".pyi": 3.0, ".ipynb": 2.0},
    "javascript": {".js": 6.0, ".mjs": 5.0, ".jsx": 4.0, ".ts": 3.0, ".tsx": 3.0},
    "typescript": {".ts": 6.0, ".tsx": 6.0, ".js": 3.0},
    "react":      {".jsx": 5.0, ".tsx": 5.0, ".js": 3.0, ".ts": 3.0},
    "vue":        {".vue": 6.0, ".js": 2.0},
    "html":       {".html": 6.0, ".htm": 5.0},
    "css":        {".css": 6.0, ".scss": 5.0, ".sass": 5.0},
    "стиль":      {".css": 6.0, ".scss": 5.0},
    "3d":         {".js": 5.0, ".html": 4.0, ".gltf": 3.0, ".glb": 3.0},
    "three":      {".js": 5.0, ".html": 3.0},
    "api":        {".py": 5.0, ".js": 4.0, ".ts": 4.0, ".go": 4.0, ".rs": 3.0},
    "server":     {".py": 5.0, ".js": 4.0, ".ts": 4.0, ".go": 4.0},
    "test":       {".py": 4.0, ".js": 4.0, ".ts": 4.0, ".test.js": 6.0, ".spec.js": 6.0},
    "docker":     {"Dockerfile": 8.0, ".yml": 4.0, ".yaml": 4.0},
    "config":     {".json": 4.0, ".yml": 4.0, ".yaml": 4.0, ".toml": 4.0, ".env": 3.0},
    "readme":     {".md": 6.0},
    "md":         {".md": 6.0},
    "docs":       {".md": 5.0, ".rst": 4.0},
    "go":         {".go": 6.0, ".mod": 4.0},
    "rust":       {".rs": 6.0, ".toml": 3.0},
    "php":        {".php": 6.0},
    "sql":        {".sql": 6.0},
}


def find_relevant_files(query: str, limit: int = 25) -> Dict[str, Any]:
    """
    Vazifa tavsifiga qarab loyiha fayllarini reyting bo'yicha tartiblab qaytaradi.
    Butun `list_dir` chiqishini o'qishdan ko'ra arzon: agent to'g'ridan-to'g'ri
    tegishli fayllarni oladi va faqat ularni `read_file` qiladi.

    Reyting: fayl nomi va yo'ldagi kalit so'z mosligi (5 ball har biriga) +
    kengaytma og'irligi (kalit so'zdan) + workspace-yaqinlik bonusi.
    """
    q = (query or "").lower().strip()
    if not q:
        return {"success": False, "error": "Query bo'sh — vazifa tavsifini bering (masalan `python api authentication`)"}

    tokens = [t for t in re.split(r"[^a-z0-9а-я]+", q) if len(t) >= 3]
    ext_weights: Dict[str, float] = {}
    for tk in tokens:
        for w in _EXT_WEIGHTS_BY_KEYWORD.get(tk, {}).items():
            ext_weights[w[0]] = max(ext_weights.get(w[0], 0), w[1])

    root = CURRENT_PROJECT_DIR.resolve()
    files, truncated = walk_project_files(root, limit=MAX_WALK_FILES * 2)
    scored: List[Dict[str, Any]] = []

    for path, rel in files:
        rel_l = rel.lower()
        score = 0.0
        matched: List[str] = []
        for tk in tokens:
            if tk in rel_l:
                score += 5.0
                matched.append(tk)
        # Kengaytma va fayl nomi bo'yicha og'irlik
        ext = path.suffix.lower()
        name = path.name
        if ext in ext_weights:
            score += ext_weights[ext]
        if name in ext_weights:
            score += ext_weights[name]
        # Test/dist/vendor pastroq priortet
        if any(p in rel_l for p in ("/test", "/spec", "__test__", "/dist", "/build", "/vendor")):
            score *= 0.6
        if score <= 0:
            continue
        try:
            size = path.stat().st_size
        except Exception:
            size = 0
        scored.append({
            "path": rel, "score": round(score, 2), "size": size,
            "matched": matched, "ext": ext or "(no ext)",
        })

    scored.sort(key=lambda x: (-x["score"], x["size"]))
    top = scored[:limit]
    return {
        "success": True,
        "query": query,
        "tokens": tokens,
        "total_scanned": len(files),
        "matched_count": len(scored),
        "results": top,
        "note": "Faylni to'liq o'qish uchun `read_file(path, mode='full')`, faqat sarlavhalar uchun `read_file(path, mode='outline')` ishlating." + (" (Ro'yxat qisqartirildi.)" if truncated else ""),
    }


def list_dir(subpath: str = "") -> Dict[str, Any]:
    """Aktiv loyiha papkasining daraxtini ko'rsatadi (papkalar bilan)."""
    try:
        root = _safe_target(subpath) if subpath else CURRENT_PROJECT_DIR.resolve()
    except Exception:
        root = CURRENT_PROJECT_DIR.resolve()

    if not root.exists():
        return {"success": True, "root": str(root), "entries": [], "note": "Papka hali bo'sh"}

    found, truncated = walk_project_files(root, limit=300, include_dirs=True)
    entries = []
    for path, rel in sorted(found, key=lambda x: x[1]):
        is_dir = path.is_dir()
        entries.append({
            "path": rel,
            "type": "dir" if is_dir else "file",
            "size": 0 if is_dir else (path.stat().st_size if path.exists() else 0)
        })

    out = {"success": True, "root": str(root), "total": len(entries), "entries": entries}
    if truncated:
        out["note"] = f"Ro'yxat {len(entries)} yozuvda kesildi — papka juda katta."
    return out


def list_files(limit: int = MAX_WALK_FILES) -> Dict[str, Any]:
    """
    Aktiv loyiha papkasi va ishchi muhitdagi fayllar ro'yxati.

    Ro'yxat chegaralangan: foydalanuvchining loyihalar papkasi 600 mingdan ortiq
    faylni o'z ichiga olishi mumkin, chegarasiz ro'yxat esa yuzlab megabaytli
    javob qaytarib, interfeysni ishdan chiqarardi.
    """
    files: List[Dict[str, Any]] = []
    seen = set()
    truncated = False

    def add_all(root: Path, label_fn, prefix: str = "", budget: int = limit):
        nonlocal truncated
        found, was_truncated = walk_project_files(root, limit=budget)
        truncated = truncated or was_truncated
        for path, rel in found:
            key = str(path)
            if key in seen:
                continue
            try:
                stat = path.stat()
            except Exception:
                continue
            seen.add(key)
            files.append({
                "name": f"{prefix}{rel}", "location": label_fn(root),
                "path": key, "size": stat.st_size, "modified": stat.st_mtime
            })

    project_root = CURRENT_PROJECT_DIR.resolve() if CURRENT_PROJECT_DIR.exists() else None
    base_root = PROJECTS_BASE_DIR.resolve() if PROJECTS_BASE_DIR.exists() else None

    # 1. Aktiv loyiha papkasi. Agar u hali ajratilmagan bo'lsa (ya'ni loyihalar
    #    bazasining o'ziga teng), butun daraxtni aylanmaymiz — faqat eng oxirgi
    #    o'zgargan bir nechta loyihani ko'rsatamiz.
    if project_root and base_root and project_root != base_root:
        add_all(project_root, lambda r: f"Ishchi muhit ({r.name})")
    elif base_root:
        try:
            recent = sorted(
                (p for p in base_root.iterdir() if p.is_dir() and not _skip_entry(p.name)),
                key=lambda p: p.stat().st_mtime, reverse=True
            )[:5]
        except Exception:
            recent = []
        per_project = max(20, limit // max(1, len(recent) or 1))
        for p in recent:
            if len(files) >= limit:
                truncated = True
                break
            add_all(p, lambda r: f"Ishchi muhit ({r.name})",
                    prefix=f"{p.name}/", budget=per_project)

    # 2. Ishchi muhit (workspace)
    if WORKSPACE_DIR.exists() and len(files) < limit:
        add_all(WORKSPACE_DIR, lambda r: "Ishchi muhit (Asosiy)",
                budget=limit - len(files))

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {
        "success": True,
        "total_files": len(files),
        "truncated": truncated,
        "files": files[:limit],
        "current_project_dir": str(CURRENT_PROJECT_DIR),
        "base_projects_dir": str(PROJECTS_BASE_DIR)
    }


def verify_code_syntax(filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Loyiha fayllarini (JavaScript, Python, HTML, CSS, JSON) statik tahlil qiladi va
    sintaksis xatolarini, e'lon qilinmagan o'zgaruvchilarni, yetishmayotgan HTML ID-larini aniqlaydi.
    """
    project_root = CURRENT_PROJECT_DIR.resolve()
    issues = []
    checked_files = []

    if filename:
        t = _safe_target(filename, CURRENT_PROJECT_DIR)
        target_files = [t] if t.exists() and t.is_file() else []
    else:
        target_files = [f for f in project_root.rglob("*") if f.is_file() and not _skip_entry(f.name)]

    # 1. HTML ID-larini yig'ish (JS bilan tekshirish uchun)
    html_files = [f for f in target_files if f.suffix.lower() in (".html", ".htm")]
    declared_ids = set()
    for hf in html_files:
        try:
            content = hf.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'\bid=["\']([a-zA-Z0-9_-]+)["\']', content):
                declared_ids.add(match.group(1))
        except Exception:
            pass

    # 2. Fayllarni tekshirish
    for f in target_files:
        ext = f.suffix.lower()
        try:
            rel = f.relative_to(project_root).as_posix()
        except Exception:
            rel = f.name
        checked_files.append(rel)

        if ext in (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                # A. Node.js syntax test
                try:
                    node_res = subprocess.run(["node", "-c", str(f)], capture_output=True, text=True, timeout=4)
                    if node_res.returncode != 0:
                        err = (node_res.stderr or node_res.stdout).strip()
                        issues.append({
                            "file": rel, "type": "SyntaxError",
                            "message": f"JavaScript/TypeScript sintaksis xatosi: {err}"
                        })
                except Exception:
                    pass

                # B. getElementById tekshiruvi (faqat HTML mavjud bo'lganda)
                for match in re.finditer(r"document\.(?:getElementById|querySelector)\(['\"]#?([a-zA-Z0-9_-]+)['\"]\)", content):
                    elem_id = match.group(1)
                    if html_files and elem_id not in declared_ids:
                        issues.append({
                            "file": rel, "type": "MissingHtmlId",
                            "message": f"JS fayl `{elem_id}` ID li elementni qidirmoqda, lekin index.html da `id=\"{elem_id}\"` mavjud emas!"
                        })

                # C. E'lon qilinmagan o'zgaruvchi bilan DOM ga murojaat
                lines = content.splitlines()
                for l_num, line in enumerate(lines, 1):
                    line_clean = line.strip()
                    m = re.match(r"^([a-zA-Z0-9_$]+)\.(style|textContent|innerHTML|addEventListener|value|classList)\b", line_clean)
                    if m:
                        var_name = m.group(1)
                        if var_name not in ("document", "window", "console", "this", "e", "event"):
                            decl_pattern = rf"\b(?:const|let|var)\s+{var_name}\b|\bfunction\s+{var_name}\b|\b{var_name}\s*="
                            if not re.search(decl_pattern, content):
                                issues.append({
                                    "file": rel, "line": l_num, "type": "UndeclaredVariable",
                                    "message": f"{l_num}-qatorda `{var_name}` ishlatilgan, lekin u fayl boshida `const {var_name} = document.getElementById(...)` bilan e'lon qilinmagan (Uncaught ReferenceError keltirib chiqaradi)!"
                                })
            except Exception as e:
                issues.append({"file": rel, "type": "ReadError", "message": f"Faylni o'qishda xatolik: {e}"})

        elif ext == ".py":
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                try:
                    ast.parse(content, filename=rel)
                except SyntaxError as se:
                    issues.append({
                        "file": rel, "line": se.lineno, "type": "SyntaxError",
                        "message": f"Python sintaksis xatosi {se.lineno}-qatorda: {se.msg}"
                    })
            except Exception as e:
                issues.append({"file": rel, "type": "ReadError", "message": f"Faylni o'qishda xatolik: {e}"})

        elif ext in (".sh", ".bash"):
            try:
                sh_res = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True, timeout=4)
                if sh_res.returncode != 0:
                    err = (sh_res.stderr or sh_res.stdout).strip()
                    issues.append({
                        "file": rel, "type": "ShellSyntaxError",
                        "message": f"Bash/Shell sintaksis xatosi: {err}"
                    })
            except Exception:
                pass

        elif ext == ".php":
            try:
                php_res = subprocess.run(["php", "-l", str(f)], capture_output=True, text=True, timeout=4)
                if php_res.returncode != 0:
                    err = (php_res.stderr or php_res.stdout).strip()
                    issues.append({
                        "file": rel, "type": "PhpSyntaxError",
                        "message": f"PHP sintaksis xatosi: {err}"
                    })
            except Exception:
                pass

        elif ext == ".go":
            try:
                go_res = subprocess.run(["go", "vet", str(f)], capture_output=True, text=True, timeout=5, cwd=str(project_root))
                if go_res.returncode != 0:
                    err = (go_res.stderr or go_res.stdout).strip()
                    if err:
                        issues.append({
                            "file": rel, "type": "GoVetError",
                            "message": f"Go tahlil xatosi: {err[:300]}"
                        })
            except Exception:
                pass

        elif ext in (".json", ".jsonc"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                json.loads(content)
            except json.JSONDecodeError as jde:
                issues.append({
                    "file": rel, "line": jde.lineno, "type": "JsonFormatError",
                    "message": f"JSON format xatosi {jde.lineno}-qatorda: {jde.msg}"
                })
            except Exception as e:
                issues.append({"file": rel, "type": "ReadError", "message": f"Faylni o'qishda xatolik: {e}"})

        elif ext in (".html", ".htm"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                for src in re.findall(r'<script\s+[^>]*src=["\']([^"\']+)["\']', content, re.IGNORECASE):
                    if not src.startswith(("http://", "https://", "//")):
                        script_path = project_root / src
                        if not script_path.exists():
                            issues.append({
                                "file": rel, "type": "MissingFile",
                                "message": f"HTML da `<script src=\"{src}\">` ko'rsatilgan, lekin `{src}` fayli papkada mavjud emas!"
                            })
                for href in re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\']', content, re.IGNORECASE):
                    if not href.startswith(("http://", "https://", "//")) and "stylesheet" in href:
                        css_path = project_root / href
                        if not css_path.exists():
                            issues.append({
                                "file": rel, "type": "MissingFile",
                                "message": f"HTML da `<link href=\"{href}\">` ko'rsatilgan, lekin `{href}` fayli papkada mavjud emas!"
                            })
            except Exception as e:
                issues.append({"file": rel, "type": "ReadError", "message": f"Faylni o'qishda xatolik: {e}"})

    return {
        "success": len(issues) == 0,
        "issues_count": len(issues),
        "issues": issues,
        "checked_files": checked_files,
        "summary": "Barcha fayllar sintaktik jihatdan to'g'ri va bog'lanishlar to'liq." if not issues else f"{len(issues)} ta xatolik aniqlandi!"
    }


# Colony Agent Memory
AGENT_MEMORY: Dict[str, Any] = {}


def set_memory(key: str, value: Any) -> Dict[str, Any]:
    AGENT_MEMORY[key] = value
    return {"success": True, "key": key}


def get_memory(key: str) -> Dict[str, Any]:
    return {"success": True, "key": key, "value": AGENT_MEMORY.get(key)}


# --- Asboblar reyestri: har birida LLM function-calling uchun JSON Schema ---

AVAILABLE_TOOLS: Dict[str, Dict[str, Any]] = {
    "write_file": {
        "name": "write_file",
        "description": (
            "Loyiha papkasiga fayl yozadi (mavjud bo'lsa ustiga yozadi). "
            "Papka ichidagi yo'llar qo'llanadi, masalan `src/app.py` — papkalar avtomatik yaratiladi. "
            "Python va JS fayllar avtomatik sintaksis tekshiruvidan o'tadi."
        ),
        "func": write_file,
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Loyihaga nisbatan yo'l, masalan `index.html` yoki `src/main.py`"},
                "content": {"type": "string", "description": "Faylning to'liq mazmuni"}
            },
            "required": ["filename", "content"]
        }
    },
    "edit_file": {
        "name": "edit_file",
        "description": (
            "Mavjud fayldagi aniq matn bo'lagini almashtiradi. Katta faylni to'liq qayta "
            "yozishdan ko'ra shuni ishlatish arzon. `old_text` faylda aynan bir marta uchrashi shart."
        ),
        "func": edit_file,
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Tahrirlanadigan fayl yo'li"},
                "old_text": {"type": "string", "description": "Almashtirilishi kerak bo'lgan aniq matn (bir marta uchrashi shart)"},
                "new_text": {"type": "string", "description": "Yangi matn"}
            },
            "required": ["filename", "old_text", "new_text"]
        }
    },
    "read_file": {
        "name": "read_file",
        "description": (
            "Fayl mazmunini o'qiydi. `mode`: `full` (to'liq, 12k belgi kesildi), "
            "`outline` (faqat class/funksiya sarlavhalari — .py/.js/.ts katta fayllar uchun), "
            "yoki `range:START-END` (aniq qatorlar oralig'i). Tahrirlashdan oldin `full` bilan o'qing."
        ),
        "func": read_file,
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "O'qiladigan fayl yo'li"},
                "mode": {"type": "string", "description": "`full` | `outline` | `range:START-END`. Default: `full`"}
            },
            "required": ["filename"]
        }
    },
    "find_relevant_files": {
        "name": "find_relevant_files",
        "description": (
            "Vazifa tavsifiga qarab loyihadagi eng tegishli fayllarni reyting bo'yicha "
            "qaytaradi. Katta loyihada `list_dir` o'rniga shuni ishlating — token tejaydi. "
            "Masalan: `find_relevant_files('python api authentication bug')`."
        ),
        "func": find_relevant_files,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Kalit so'zlar (til, komponent nomi, xato tavsifi)"},
                "limit": {"type": "integer", "description": "Nechta natija qaytarilsin (default 25)"}
            },
            "required": ["query"]
        }
    },
    "list_dir": {
        "name": "list_dir",
        "description": "Loyiha papkasining fayl va papkalar daraxtini qaytaradi.",
        "func": list_dir,
        "parameters": {
            "type": "object",
            "properties": {
                "subpath": {"type": "string", "description": "Ixtiyoriy ichki papka; bo'sh bo'lsa loyiha ildizi"}
            },
            "required": []
        }
    },
    "verify_code_syntax": {
        "name": "verify_code_syntax",
        "description": "Loyiha fayllaridagi (JS, Python, HTML, CSS) barcha sintaksis xatolar, e'lon qilinmagan o'zgaruvchilar va yo'qolgan HTML ID larini aniqlaydi.",
        "func": verify_code_syntax,
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Ixtiyoriy bitta fayl nomi, bo'sh bo'lsa butun loyiha tekshiriladi"}
            },
            "required": []
        }
    },
    "run_shell_command": {
        "name": "run_shell_command",
        "description": (
            "Terminalda buyruq bajaradi (loyiha papkasida). Testlarni yurgizish, paket o'rnatish, "
            "linter ishga tushirish uchun. Interaktiv buyruqlar qo'llanmaydi."
        ),
        "func": run_shell_command,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bajarilishi kerak bo'lgan shell buyrug'i"},
                "timeout": {"type": "integer", "description": "Maksimal kutish vaqti sekundda (default 60)"}
            },
            "required": ["command"]
        }
    },
    "execute_python": {
        "name": "execute_python",
        "description": "Python kodini ishga tushiradi va stdout/stderr qaytaradi. Kod avval sintaksis bo'yicha tekshiriladi.",
        "func": execute_python,
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Bajarilishi kerak bo'lgan Python kodi"},
                "timeout": {"type": "integer", "description": "Maksimal kutish vaqti sekundda (default 30)"}
            },
            "required": ["code"]
        }
    },
    "calculate": {
        "name": "calculate",
        "description": "Matematik ifodani hisoblaydi (math moduli funksiyalari qo'llanadi).",
        "func": calculate,
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Masalan `sqrt(144) + 3**2`"}
            },
            "required": ["expression"]
        }
    },
    "list_files": {
        "name": "list_files",
        "description": "Barcha loyihalar va ishchi muhitdagi fayllar ro'yxatini qaytaradi.",
        "func": list_files,
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}


def get_tool_schemas(names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """LLM'ga yuborish uchun sof JSON Schema ro'yxati (`func` kalitisiz)."""
    selected = names or list(AVAILABLE_TOOLS.keys())
    schemas = []
    for n in selected:
        t = AVAILABLE_TOOLS.get(n)
        if not t:
            continue
        schemas.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": t.get("parameters", {"type": "object", "properties": {}})
        })
    return schemas


def render_tool_guide(names: Optional[List[str]] = None) -> str:
    """
    Asbob sxemalaridan prompt uchun qo'llanma matni yasaydi.
    Native function-calling ishlamagan modellar uchun zaxira protokol.
    """
    lines = ["## Sizga berilgan asboblar", ""]
    for schema in get_tool_schemas(names):
        params = schema.get("parameters", {}).get("properties", {})
        required = set(schema.get("parameters", {}).get("required", []))
        arg_desc = ", ".join(
            f"{k}{'' if k in required else '?'}: {v.get('type', 'string')}"
            for k, v in params.items()
        ) or "(argumentsiz)"
        lines.append(f"- **`{schema['name']}`**({arg_desc}) — {schema['description']}")
    lines += [
        "",
        "## Asbobni chaqirish formati",
        "Agar tizim native function-calling qo'llasa, oddiy tarzda funksiyani chaqiring.",
        "Aks holda javobingizga aynan quyidagi blokni qo'shing (bir xabarda bir nechta blok bo'lishi mumkin):",
        "",
        "```tool_call",
        '{"tool": "write_file", "params": {"filename": "src/main.py", "content": "print(1)"}}',
        "```",
        "",
        "Ish tugagach, asbob chaqirmasdan yakuniy xulosani yozing va oxirida `TASK_COMPLETE` deb belgilang.",
    ]
    return "\n".join(lines)


def execute_tool(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Asbobni himoyalangan tarzda bajaradi — noto'g'ri argument agentga tushunarli xato qaytaradi."""
    tool = AVAILABLE_TOOLS.get(name)
    if not tool:
        return {
            "success": False,
            "error": f"`{name}` nomli asbob yo'q. Mavjudlari: {', '.join(AVAILABLE_TOOLS)}"
        }

    schema = tool.get("parameters", {})
    allowed = set(schema.get("properties", {}).keys())
    required = set(schema.get("required", []))
    params = params if isinstance(params, dict) else {}

    missing = required - set(params.keys())
    if missing:
        return {
            "success": False,
            "error": f"`{name}` uchun majburiy argument(lar) yetishmaydi: {', '.join(sorted(missing))}"
        }

    filtered = {k: v for k, v in params.items() if k in allowed}
    try:
        return tool["func"](**filtered)
    except TypeError as e:
        return {"success": False, "error": f"`{name}` argumentlari mos kelmadi: {e}"}
    except Exception as e:
        return {"success": False, "error": f"`{name}` bajarilishida xatolik: {type(e).__name__}: {e}"}
