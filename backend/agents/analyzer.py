import json
from typing import Dict, Any
from ..llm_client import LLMClient, parse_json_object
from pathlib import Path
from ..config import settings


def _clamp_dim(value, default):
    try:
        return max(400, min(2400, int(value)))
    except (TypeError, ValueError):
        return default


class AnalyzerAgent:
    """Stage 1: turns any free-text request into a structured visual brief."""

    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/analyzer.txt"
        self.prompt_text = p.read_text()

    def analyze(self, user_prompt: str, width: int = None, height: int = None, brand: str = None) -> Dict[str, Any]:
        print("[AGENT] Brief input:", user_prompt)
        request = "User request:\n" + user_prompt
        if width and height:
            request += f"\n\nRequired canvas size: {width} x {height} pixels."
        if brand:
            request += f"\n\nCredit line the user asked for: {brand}"
        raw = self.llm.generate_text(
            request,
            system=self.prompt_text,
            model=settings.model_for("brief"),
            json_mode=True,
            max_output_tokens=10000,
            temperature=0.4,
        )
        brief = parse_json_object(raw)

        # Explicit user choices win over the model's guess.
        if width and height:
            brief["width"], brief["height"] = width, height
        brief["width"] = _clamp_dim(brief.get("width"), 1080)
        brief["height"] = _clamp_dim(brief.get("height"), 1350)
        if brand:
            brief["brand"] = brand
        if str(brief.get("brand") or "").strip().lower() in ("", "unknown brand", "none", "null", "n/a", "brand"):
            brief["brand"] = None
        print("[AGENT] Brief:", json.dumps(brief, indent=2, ensure_ascii=False))
        return brief
