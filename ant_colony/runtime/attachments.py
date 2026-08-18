"""
Foydalanuvchi materiallari: fayl, ZIP arxiv yoki mavjud papka yo'li.

Oqim:
  1. Foydalanuvchi PM konsoliga fayl/ZIP yuklaydi yoki papka yo'lini beradi.
  2. Bu modul materialni ish maydoniga tayyorlaydi (ZIP xavfsiz ochiladi).
  3. Agentlarga fayl daraxti va matn parchalaridan iborat kontekst beriladi.
  4. Ish tugagach natija foydalanuvchi bergan formatda qaytariladi:
       ZIP kirdi  -> ZIP chiqadi
       bitta fayl -> o'sha fayl (yoki tahrirlangani)
       papka yo'li -> joyida tahrirlanadi, arxiv ixtiyoriy.
"""
import mimetypes
import os
import shutil
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ant_colony.config import DATA_DIR, PROJECTS_BASE_DIR

UPLOAD_ROOT: Path = DATA_DIR / "uploads"

# --- Cheklovlar (zip bomb va disk to'lishiga qarshi) ---
MAX_UPLOAD_BYTES = 200 * 1024 * 1024        # bitta yuklanma
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024     # ochilgandan keyingi umumiy hajm
MAX_EXTRACTED_FILES = 5000
MAX_COMPRESSION_RATIO = 200                 # ochilgan/siqilgan nisbati

# Agentga matn sifatida ko'rsatiladigan fayl turlari.
TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".env", ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm",
    ".css", ".scss", ".sass", ".sql", ".sh", ".bash", ".zsh", ".rb", ".go", ".rs",
    ".java", ".kt", ".c", ".h", ".cpp", ".hpp", ".cs", ".php", ".swift", ".dart",
    ".vue", ".svelte", ".xml", ".csv", ".tsv", ".gitignore", ".dockerfile",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}

# Ochishda o'tkazib yuboriladigan yo'llar.
SKIP_PARTS = {"__MACOSX", ".git", "node_modules", ".venv", "venv", "__pycache__", ".DS_Store"}


class AttachmentError(ValueError):
    """Yuklangan material qabul qilinmadi (foydalanuvchiga ko'rsatiladi)."""


@dataclass
class AttachmentFile:
    path: str            # ish papkasiga nisbatan yo'l
    size: int
    kind: str            # "text" | "image" | "binary"


@dataclass
class Attachment:
    """Bitta yuklanma yoki papka haqida to'liq ma'lumot."""

    id: str
    kind: str                       # "zip" | "file" | "directory"
    original_name: str
    work_dir: str                   # agentlar ishlaydigan papka
    files: List[AttachmentFile] = field(default_factory=list)
    total_bytes: int = 0
    truncated: bool = False
    created_at: float = 0.0
    # ZIP kirgan bo'lsa natijani ham ZIP qilib qaytaramiz.
    return_as: str = "none"         # "zip" | "file" | "none"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["files"] = [asdict(f) for f in self.files]
        return data


def _safe_root() -> Path:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return UPLOAD_ROOT


def _classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in TEXT_SUFFIXES or path.name.lower() in ("dockerfile", "makefile", "readme"):
        return "text"
    guess = mimetypes.guess_type(path.name)[0] or ""
    if guess.startswith("text/"):
        return "text"
    if guess.startswith("image/"):
        return "image"
    return "binary"


def _should_skip(rel_parts: tuple) -> bool:
    return any(part in SKIP_PARTS or part.startswith("._") for part in rel_parts)


def _is_within(base: Path, target: Path) -> bool:
    """Yo'l `base` ichidami? Zip Slip (../../) hujumiga qarshi asosiy tekshiruv."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _inventory(work_dir: Path) -> tuple:
    """Papkadagi fayllar ro'yxati va umumiy hajmi."""
    files: List[AttachmentFile] = []
    total = 0
    truncated = False

    for root, dirnames, filenames in os.walk(work_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS and not d.startswith("._")]
        for name in sorted(filenames):
            full = Path(root) / name
            rel = full.relative_to(work_dir)
            if _should_skip(rel.parts):
                continue
            try:
                size = full.stat().st_size
            except OSError:
                continue
            files.append(AttachmentFile(path=str(rel), size=size, kind=_classify(full)))
            total += size
            if len(files) >= MAX_EXTRACTED_FILES:
                truncated = True
                break
        if truncated:
            break

    files.sort(key=lambda f: f.path)
    return files, total, truncated


def _extract_zip(archive: Path, work_dir: Path) -> None:
    """
    ZIP'ni xavfsiz ochadi.

    Himoyalar:
      * Zip Slip — arxiv ichidagi `../` yo'llari ish papkasidan chiqib keta olmaydi;
      * zip bomb — ochilgan umumiy hajm va siqilish nisbati cheklanadi;
      * symlink yozuvlari umuman ochilmaydi.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_EXTRACTED_FILES:
            raise AttachmentError(
                f"В архиве слишком много файлов ({len(infos)}). Лимит — {MAX_EXTRACTED_FILES}."
            )

        planned = sum(i.file_size for i in infos)
        if planned > MAX_EXTRACTED_BYTES:
            raise AttachmentError(
                f"Распакованный размер {planned // (1024 * 1024)} МБ превышает лимит "
                f"{MAX_EXTRACTED_BYTES // (1024 * 1024)} МБ."
            )
        compressed = sum(i.compress_size for i in infos) or 1
        if planned / compressed > MAX_COMPRESSION_RATIO:
            raise AttachmentError("Архив отклонён: подозрительная степень сжатия (zip bomb).")

        for info in infos:
            if info.is_dir():
                continue
            # Symlink yozuvlari (yuqori 4 bit = 0xA) — o'tkazib yuboramiz.
            if (info.external_attr >> 28) == 0xA:
                continue

            rel = Path(info.filename)
            if rel.is_absolute() or _should_skip(rel.parts):
                continue

            target = work_dir / rel
            if not _is_within(work_dir, target):
                raise AttachmentError(f"Архив содержит небезопасный путь: {info.filename}")

            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 64)


def ingest_upload(filename: str, data: bytes) -> Attachment:
    """
    Yuklangan faylni qabul qiladi. ZIP bo'lsa ochadi, aks holda o'zini saqlaydi.
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise AttachmentError(
            f"Файл больше {MAX_UPLOAD_BYTES // (1024 * 1024)} МБ — загрузите архив поменьше "
            f"или укажите путь к папке."
        )
    if not data:
        raise AttachmentError("Файл пуст.")

    att_id = uuid.uuid4().hex[:12]
    base = _safe_root() / att_id
    work_dir = base / "workspace"
    work_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename or "upload.bin").name
    is_zip = safe_name.lower().endswith(".zip")

    if is_zip:
        archive_path = base / safe_name
        archive_path.write_bytes(data)
        try:
            _extract_zip(archive_path, work_dir)
        except zipfile.BadZipFile as exc:
            raise AttachmentError("Файл не является корректным ZIP-архивом.") from exc
        kind, return_as = "zip", "zip"
    else:
        (work_dir / safe_name).write_bytes(data)
        kind, return_as = "file", "file"

    files, total, truncated = _inventory(work_dir)
    if not files:
        raise AttachmentError("После распаковки не осталось файлов для работы.")

    return Attachment(
        id=att_id, kind=kind, original_name=safe_name, work_dir=str(work_dir),
        files=files, total_bytes=total, truncated=truncated,
        created_at=time.time(), return_as=return_as,
    )


def ingest_path(raw_path: str) -> Attachment:
    """
    Foydalanuvchi bergan papka (yoki fayl) yo'lini qabul qiladi.

    Xavfsizlik: yo'l loyihalar papkasi yoki uy katalogi ichida bo'lishi kerak —
    aks holda agentlar butun fayl tizimini o'zgartira olardi.
    """
    raw = (raw_path or "").strip()
    if not raw:
        raise AttachmentError("Путь пуст.")

    target = Path(raw).expanduser()
    if not target.exists():
        raise AttachmentError(f"Путь не найден: {target}")

    resolved = target.resolve()
    allowed_roots = [PROJECTS_BASE_DIR.resolve(), Path.home().resolve()]
    if not any(_is_within(root, resolved) for root in allowed_roots):
        raise AttachmentError(
            "Разрешены только пути внутри рабочей папки проектов или домашнего каталога."
        )

    if resolved.is_file():
        files = [AttachmentFile(path=resolved.name, size=resolved.stat().st_size,
                                kind=_classify(resolved))]
        return Attachment(
            id=uuid.uuid4().hex[:12], kind="file", original_name=resolved.name,
            work_dir=str(resolved.parent), files=files, total_bytes=files[0].size,
            created_at=time.time(), return_as="file",
        )

    files, total, truncated = _inventory(resolved)
    if not files:
        raise AttachmentError("В указанной папке нет файлов.")

    return Attachment(
        id=uuid.uuid4().hex[:12], kind="directory", original_name=resolved.name,
        work_dir=str(resolved), files=files, total_bytes=total, truncated=truncated,
        created_at=time.time(), return_as="none",
    )


def build_agent_context(att: Attachment, max_chars: int = 12000) -> str:
    """
    Agentlar uchun matnli kontekst: fayl daraxti + kichik matn fayllarining mazmuni.

    Bu PM'ga "strategik fikrlash" uchun kerak: u nima berilganini ko'rmasa,
    rejani taxminga qurishga majbur bo'ladi.
    """
    work = Path(att.work_dir)
    lines: List[str] = []
    lines.append(f"ПОЛЬЗОВАТЕЛЬ ПРИЛОЖИЛ МАТЕРИАЛЫ ({att.kind}): {att.original_name}")
    lines.append(f"Рабочая папка: {att.work_dir}")
    lines.append(f"Файлов: {len(att.files)}, общий размер: {att.total_bytes // 1024} КБ")
    if att.truncated:
        lines.append("(список файлов усечён — показаны не все)")
    lines.append("")
    lines.append("СТРУКТУРА:")
    for f in att.files[:200]:
        lines.append(f"  {f.path}  [{f.kind}, {f.size} B]")
    if len(att.files) > 200:
        lines.append(f"  ... ещё {len(att.files) - 200} файлов")

    # Kichik matn fayllarini to'liqroq ko'rsatamiz — kod bilan ishlash uchun asosiy manba.
    budget = max_chars
    previews: List[str] = []
    for f in att.files:
        if f.kind != "text" or f.size > 60_000 or budget <= 0:
            continue
        full = work / f.path
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunk = content[: min(4000, budget)]
        budget -= len(chunk)
        previews.append(f"\n--- {f.path} ---\n{chunk}")
        if len(content) > len(chunk):
            previews.append(f"\n[... файл обрезан, всего {len(content)} символов]")

    if previews:
        lines.append("")
        lines.append("СОДЕРЖИМОЕ ТЕКСТОВЫХ ФАЙЛОВ:")
        lines.extend(previews)

    images = [f.path for f in att.files if f.kind == "image"]
    if images:
        lines.append("")
        lines.append("ИЗОБРАЖЕНИЯ (доступны в рабочей папке): " + ", ".join(images[:20]))

    return "\n".join(lines)


def package_result(att: Attachment) -> Optional[Dict[str, Any]]:
    """
    Ish tugagach natijani foydalanuvchi bergan formatda tayyorlaydi.

    ZIP kirgan bo'lsa — o'zgartirilgan papka qayta arxivlanadi.
    Bitta fayl bo'lsa — o'sha fayl qaytariladi.
    """
    work = Path(att.work_dir)
    if not work.exists():
        return None

    if att.return_as == "zip":
        out_dir = _safe_root() / att.id
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(att.original_name).stem or "result"
        out_zip = out_dir / f"{stem}_updated.zip"

        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirnames, filenames in os.walk(work):
                dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS]
                for name in filenames:
                    full = Path(root) / name
                    rel = full.relative_to(work)
                    if _should_skip(rel.parts):
                        continue
                    zf.write(full, str(rel))

        return {
            "kind": "zip",
            "name": out_zip.name,
            "path": str(out_zip),
            "size": out_zip.stat().st_size,
            "download_url": f"/api/attachments/{att.id}/download",
        }

    if att.return_as == "file":
        files, _total, _trunc = _inventory(work)
        if not files:
            return None
        # Bir nechta fayl paydo bo'lgan bo'lsa (agent qo'shimcha yaratgan) — arxivlaymiz.
        if len(files) > 1:
            att.return_as = "zip"
            return package_result(att)
        single = work / files[0].path
        return {
            "kind": "file",
            "name": single.name,
            "path": str(single),
            "size": single.stat().st_size,
            "download_url": f"/api/attachments/{att.id}/download",
        }

    return None


def cleanup_old(max_age_s: float = 24 * 3600) -> int:
    """Eski yuklanmalarni o'chiradi (disk to'lib qolmasin)."""
    root = _safe_root()
    removed = 0
    now = time.time()
    for child in root.iterdir():
        try:
            if child.is_dir() and (now - child.stat().st_mtime) > max_age_s:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed
