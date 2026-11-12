import json
from typing import Dict
from ..llm_client import LLMClient, parse_json_object
from pathlib import Path
from ..config import settings


class CreativeDirectorAgent:
    """Stage 2: turns the brief into a layered shot plan (lighting, depth, materials, type)."""

    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/creative_director.txt"
        self.prompt_text = p.read_text()

    def decide(self, analysis: Dict) -> Dict:
        raw = self.llm.generate_text(
            "Brief JSON:\n" + json.dumps(analysis, ensure_ascii=False, indent=2),
            system=self.prompt_text,
            model=settings.model_for("director"),
            json_mode=True,
            max_output_tokens=16000,
            temperature=0.8,
        )
        plan = parse_json_object(raw)
        # The canvas is fixed by the brief; the director must not change it.
        plan["canvas"] = {"width": analysis["width"], "height": analysis["height"]}
        if not analysis.get("brand"):
            plan["text_blocks"] = [b for b in plan.get("text_blocks") or [] if b.get("role") != "brand"]
        print("[AGENT] Shot plan:", json.dumps(plan, indent=2, ensure_ascii=False))
        return plan
