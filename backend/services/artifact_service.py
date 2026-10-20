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


def get_artifact_path(gen_id: str, filename: str) -> Optional[Path]:
    candidate = ROOT / gen_id / filename
    try:
        candidate.resolve()
    except Exception:
        return None
    if candidate.exists():
        return candidate
    return None
