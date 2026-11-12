import json
from typing import Dict, List
from ..llm_client import LLMClient, parse_json_object
from pathlib import Path
from ..config import settings


class ReviewerAgent:
    """Compile stage QA: looks at the rendered PNG and returns fix notes for the Code Writer."""

    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/reviewer.txt"
        self.prompt_text = p.read_text()

    def review(self, analysis: Dict, creative: Dict, png: bytes, console_errors: List[str]) -> Dict:
        prompt = (
            "Brief JSON:\n" + json.dumps(analysis, ensure_ascii=False)
            + "\n\nShot plan JSON:\n" + json.dumps(creative, ensure_ascii=False)
            + "\n\nBrowser console errors: " + (" | ".join(console_errors[:5]) if console_errors else "none")
            + "\n\nThe rendered image is attached. Review it."
        )
        raw = self.llm.generate_text(
            prompt,
            system=self.prompt_text,
            model=settings.model_for("reviewer"),
            json_mode=True,
            max_output_tokens=12000,
            temperature=0.2,
            images=[png],
        )
        result = parse_json_object(raw)
        result.setdefault("issues", [])
        result["pass"] = bool(result.get("pass")) and not any(i.get("severity") == "high" for i in result["issues"])
        print("[AGENT] Review:", json.dumps(result, indent=2, ensure_ascii=False))
        return result
