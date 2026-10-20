import json
from typing import Dict, Any
from ..llm_client import LLMClient, LLMClientError
from pathlib import Path
from ..config import settings


class AnalyzerAgent:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/analyzer.txt"
        self.prompt_text = p.read_text()

    def analyze(self, user_prompt: str, retries: int = 1) -> Dict[str, Any]:
        print("[AGENT] Analyzer input:", user_prompt)
        prompt = self.prompt_text + "\nUser request:\n" + user_prompt
        print("[AGENT] Analyzer prompt:\n", prompt)
        raw = self.llm.generate_text(prompt, max_retries=retries or settings.MAX_AGENT_RETRIES, response_mime_type="application/json", max_output_tokens=1200)
        print("[AGENT] Analyzer raw output start")
        print(raw[:2000])
        print("[AGENT] Analyzer raw output end")
        if not raw:
            raise LLMClientError("Analyzer returned empty result")

        # Try to recover from slight formatting issues around the JSON payload.
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        if cleaned.startswith("\n"):
            cleaned = cleaned.lstrip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start:end+1])
            raise LLMClientError(f"Analyzer output was not valid JSON: {raw[:500]}")
