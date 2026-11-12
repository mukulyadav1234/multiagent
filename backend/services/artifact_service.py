import os
import uuid
from pathlib import Path
from typing import Optional

from ..config import settings


ROOT = Path(settings.OUTPUT_DIR)
ROOT.mkdir(parents=True, exist_ok=True)


def create_generation_dir() -> Path:
    gen_id = uuid.uuid4().hex
    p = ROOT / gen_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_html(gen_dir: Path, html: str, filename: str = "poster.html") -> Path:
    path = gen_dir / filename
    path.write_text(html, encoding="utf-8")
    return path


def get_generation_dir(gen_id: str) -> Optional[Path]:
    gen_root = (ROOT / gen_id).resolve()
    if gen_root.parent != ROOT.resolve() or not gen_root.is_dir():
        return None
    return gen_root


def get_artifact_path(gen_id: str, filename: str) -> Optional[Path]:
    # Reject "../" tricks: the file must stay inside this generation's folder.
    gen_root = (ROOT / gen_id).resolve()
    candidate = (gen_root / filename).resolve()
    if gen_root.parent != ROOT.resolve() or gen_root not in candidate.parents:
        return None
    if candidate.is_file():
        return candidate
    return None
