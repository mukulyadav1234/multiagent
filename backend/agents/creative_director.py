import json
from typing import Dict
from ..llm_client import LLMClient
from pathlib import Path
from ..config import settings


class CreativeDirectorAgent:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/creative_director.txt"
        self.prompt_text = p.read_text()

    def _fallback_creative(self, analysis: Dict) -> Dict:
        brand = str(analysis.get("brand") or "Brand")
        occasion = str(analysis.get("occasion") or "Celebration").lower()
        headline = f"Happy {occasion.title()}"
        subheadline = "Celebrate with joy, purpose, and memorable moments"
        palette = ["#0D1B2A", "#D9A441", "#F8F1E7"]
        layout = "Premium editorial campaign layout"
        elements = ["Hero visual", "Branded headline", "Clean product or event framing"]
        footer = f"Warm wishes from {brand}"

        if "holi" in occasion:
            headline = "HAPPY HOLI"
            subheadline = "May your world be filled with colour, joy and new beginnings."
            palette = ["#FF5CA8", "#FF8A00", "#FDE047", "#29C7F5", "#6B4BFF"]
            layout = "Vibrant festival poster with explosive coloured gulal and layered spatial depth"
            elements = ["exploding gulal clouds", "colour splash bursts", "joyful festival energy", "brand signature treatment"]
            footer = f"NGY celebrates colour and community"
        elif "ai" in occasion or "technology" in occasion or "event" in occasion:
            headline = "NEXT-GEN AI"
            subheadline = "Smarter systems, sharper ideas, better outcomes."
            palette = ["#0F172A", "#6EE7F9", "#8B5CF6", "#F8FAFC"]
            layout = "Cinematic tech campaign with bold typography and structural depth"
            elements = ["abstract AI signal pattern", "modern data flow", "precision lighting", "clean product framing"]
            footer = f"Built for {brand}"
        elif "recruit" in occasion or "career" in occasion or "job" in occasion:
            headline = "JOIN OUR TEAM"
            subheadline = "Build a career that grows with purpose and ambition."
            palette = ["#0F172A", "#2563EB", "#E2E8F0", "#F8FAFC"]
            layout = "Professional recruitment campaign with confident editorial structure"
            elements = ["professional portrait", "confident corporate framing", "clean company identity", "positive momentum"]
            footer = f"Explore opportunities at {brand}"
        elif "diwali" in occasion:
            headline = "Happy Diwali"
            subheadline = "May this festive season bring light, prosperity, and success"
            palette = ["#10182B", "#D4AF67", "#FFF3D6"]
            layout = "Warm celebratory festival poster with premium glow"
            elements = ["glowing diya", "warm festive glow", "golden lighting", "ornamental festival framing"]
            footer = f"Warm wishes from {brand}"
        elif "christmas" in occasion:
            headline = "Merry Christmas"
            subheadline = "Season’s greetings and a joyful celebration"
            palette = ["#0F172A", "#E11D48", "#FDF2F8"]
            layout = "Warm seasonal celebration with bold festive contrast"
            elements = ["holiday lights", "seasonal warmth", "premium centered framing", "joyful typography"]
            footer = f"Warm wishes from {brand}"

        return {
            "headline": headline,
            "subheadline": subheadline,
            "brand": brand,
            "palette": palette,
            "layout": layout,
            "elements": elements,
            "footer": footer,
        }

    def _parse_json(self, out: str, analysis: Dict) -> Dict:
        cleaned = out.strip()
        if not cleaned:
            return self._fallback_creative(analysis)

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(cleaned)
            if isinstance(result, dict) and "headline" in result and "subheadline" in result:
                return result
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            candidate = cleaned[start:end + 1]
            try:
                result = json.loads(candidate)
                if isinstance(result, dict) and "headline" in result and "subheadline" in result:
                    return result
            except Exception:
                pass

        return self._fallback_creative(analysis)

    def decide(self, analysis: Dict, retries: int = 1) -> Dict:
        prompt = self.prompt_text + "\nAnalyzer JSON:\n" + json.dumps(analysis)
        print("[AGENT] Creative Director prompt:\n", prompt)
        out = self.llm.generate_text(
            prompt,
            max_retries=retries or settings.MAX_AGENT_RETRIES,
            response_mime_type="application/json",
            max_output_tokens=800,
        )
        print("[AGENT] Creative Director raw output start")
        print(out[:2000])
        print("[AGENT] Creative Director raw output end")
        result = self._parse_json(out, analysis)
        print("[AGENT] Creative Director final JSON:\n", json.dumps(result, indent=2))
        return result
