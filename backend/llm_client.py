import os
import time
import warnings
import requests
from typing import Optional

from .config import settings


class LLMClientError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        if not self.api_key:
            raise LLMClientError("Missing GEMINI_API_KEY in environment; set it in .env")

    def generate_text(
        self,
        prompt: str,
        max_retries: int = 1,
        response_mime_type: Optional[str] = None,
        max_output_tokens: int = 800,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if response_mime_type:
            body["generationConfig"]["responseMimeType"] = response_mime_type

        verify = settings.SSL_VERIFY
        if not verify:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        last_exc = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=(10, 120),
                    verify=verify,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_parts = []
                        for p in parts:
                            if isinstance(p, dict) and "text" in p:
                                text_parts.append(p["text"])
                        if text_parts:
                            return "".join(text_parts)
                    raise LLMClientError("Gemini response was empty or malformed")
                else:
                    last_exc = LLMClientError(f"LLM request failed {resp.status_code}: {resp.text}")
            except requests.exceptions.Timeout as e:
                last_exc = LLMClientError(f"Gemini request timed out after 120 seconds. Check network/proxy/firewall. Details: {e}")
            except Exception as e:
                last_exc = e
            time.sleep(1 + attempt)

        raise last_exc or LLMClientError("Unknown LLM client error")
