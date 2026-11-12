import json
from typing import Dict, List, Optional
from ..llm_client import LLMClient, LLMClientError
from pathlib import Path
from ..config import settings


def extract_html(raw: str) -> str:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    lower = cleaned.lower()
    start = lower.find("<!doctype")
    if start == -1:
        start = lower.find("<html")
    end = lower.rfind("</html>")
    if start == -1 or end == -1:
        raise LLMClientError("Code Writer did not return a complete HTML document (missing <html> or </html>)")
    return cleaned[start:end + len("</html>")]


class CodeWriterAgent:
    """Stage 3: paints the shot plan as HTML + inline SVG + CSS, and revises it from review notes."""

    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/code_writer.txt"
        self.prompt_text = p.read_text()

    def _generate(self, prompt: str) -> str:
        raw = self.llm.generate_text(
            prompt,
            system=self.prompt_text,
            model=settings.model_for("coder"),
            max_output_tokens=settings.CODER_MAX_TOKENS,
            temperature=0.6,
        )
        html = extract_html(raw)
        print(f"[AGENT] Code Writer produced {len(html)} chars of HTML")
        return html

    def write(self, analysis: Dict, creative: Dict) -> str:
        prompt = (
            "Brief JSON:\n" + json.dumps(analysis, ensure_ascii=False, indent=2)
            + "\n\nShot plan JSON:\n" + json.dumps(creative, ensure_ascii=False, indent=2)
            + f"\n\nCanvas: {analysis['width']} x {analysis['height']} px. Paint it now."
        )
        return self._generate(prompt)

    def revise(self, analysis: Dict, creative: Dict, html: str, issues: List[Dict], console_errors: Optional[List[str]] = None) -> str:
        notes = "\n".join(f"- [{i.get('severity')}/{i.get('area')}] {i.get('problem')} -> FIX: {i.get('fix')}" for i in issues)
        if console_errors:
            notes += "\n- [high/technical] Browser console errors: " + " | ".join(console_errors[:5])
        prompt = (
            "Brief JSON:\n" + json.dumps(analysis, ensure_ascii=False, indent=2)
            + "\n\nShot plan JSON:\n" + json.dumps(creative, ensure_ascii=False, indent=2)
            + "\n\nCurrent HTML:\n" + html
            + "\n\nThe art director reviewed the rendered image and wants these changes:\n" + notes
            + "\n\nReturn the complete revised HTML document. Keep everything that already works; fix every note."
        )
        return self._generate(prompt)
