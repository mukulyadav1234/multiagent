import base64
import json
import time
import warnings
import requests
from typing import List, Optional

from .config import settings


class LLMClientError(Exception):
    pass


class _StreamDropped(Exception):
    """Stream failed before any text arrived; safe to retry the whole request."""


def parse_json_object(raw: str) -> dict:
    """Pull the first JSON object out of a model reply (tolerates ``` fences and chatter)."""
    if not raw or not raw.strip():
        raise LLMClientError("Model returned an empty reply")
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMClientError(f"Model reply was not JSON: {raw[:300]}")
        try:
            result = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as e:
            raise LLMClientError(f"Model reply was not valid JSON ({e}): {raw[:300]}")
    if not isinstance(result, dict):
        raise LLMClientError("Model reply was JSON but not an object")
    return result


def _openrouter_chunk(chunk):
    """-> (text, finish_reason, model, usage) for one OpenRouter stream chunk."""
    text, finish = "", None
    for choice in chunk.get("choices") or []:
        text += (choice.get("delta") or {}).get("content") or ""
        finish = choice.get("finish_reason") or finish
    return text, finish, chunk.get("model"), chunk.get("usage")


def _gemini_chunk(chunk):
    """-> (text, finish_reason, model, usage) for one Gemini stream chunk."""
    text, finish = "", None
    for cand in chunk.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if not part.get("thought"):
                text += part.get("text", "")
        reason = cand.get("finishReason")
        if reason:
            finish = "length" if reason == "MAX_TOKENS" else "stop" if reason == "STOP" else reason
    meta = chunk.get("usageMetadata")
    usage = {"prompt_tokens": meta.get("promptTokenCount"), "completion_tokens": meta.get("candidatesTokenCount"),
             "thinking_tokens": meta.get("thoughtsTokenCount")} if meta else None
    return text, finish, chunk.get("modelVersion"), usage


class LLMClient:
    """Chat client for Gemini (default) or OpenRouter, chosen by LLM_PROVIDER.

    `model` is a model id or a comma-separated fallback chain; each agent passes its own via
    settings.model_for(role). Replies are streamed so long generations survive proxy drops.
    """

    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.provider = provider or settings.provider()
        self.api_key = api_key or (settings.GEMINI_API_KEY if self.provider == "gemini" else settings.OPENROUTER_API_KEY)
        if not self.api_key:
            name = "GEMINI_API_KEY" if self.provider == "gemini" else "OPENROUTER_API_KEY"
            raise LLMClientError(f"Missing {name} in environment; set it in .env")
        self.verify = settings.requests_verify()
        if self.verify is False:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    def generate_text(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        max_output_tokens: int = 4000,
        temperature: float = 0.7,
        images: Optional[List[bytes]] = None,
        max_retries: int = None,
        max_continuations: int = 2,
    ) -> str:
        """Return the full reply. If it stops early (token limit or dropped stream), ask the model to continue."""
        max_retries = max_retries or settings.MAX_AGENT_RETRIES
        chain = [m.strip() for m in (model or settings.model_for("coder")).split(",") if m.strip()]
        text, finish = self._call(prompt, system, chain, json_mode, max_output_tokens, temperature, images, max_retries, None)
        for _ in range(max_continuations):
            if finish != "length":
                break
            print(f"[LLM] reply incomplete at {len(text)} chars (token limit or dropped stream), requesting continuation")
            more, finish = self._call(prompt, system, chain, json_mode, max_output_tokens, temperature, images, max_retries, text)
            text += more
        if finish == "length":
            raise LLMClientError("Model reply was still incomplete after continuation (token limit or repeated connection drops)")
        if finish not in (None, "stop", "length"):
            print(f"[LLM] reply ended with finish reason {finish}")
        return text

    def _call(self, prompt, system, chain, json_mode, max_tokens, temperature, images, max_retries, partial):
        if self.provider == "gemini":
            return self._call_gemini(prompt, system, chain, json_mode, max_tokens, temperature, images, max_retries, partial)
        return self._call_openrouter(prompt, system, chain, json_mode, max_tokens, temperature, images, max_retries, partial)

    def _call_openrouter(self, prompt, system, chain, json_mode, max_tokens, temperature, images, max_retries, partial):
        user_content = [{"type": "text", "text": prompt}]
        for img in images or []:
            b64 = base64.b64encode(img).decode()
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_content})
        if partial:
            messages.append({"role": "assistant", "content": partial})
            messages.append({"role": "user", "content": CONTINUE_PROMPT})

        body = {"messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": True}
        if len(chain) > 1:
            body["models"] = chain  # OpenRouter falls through the list on rate limits / outages
        else:
            body["model"] = chain[0]
        if json_mode and not partial:
            body["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "AI Poster Studio",
        }
        targets = [(f"{settings.OPENROUTER_BASE_URL}/chat/completions", body, ",".join(chain))]
        return self._post(targets, headers, max_retries, _openrouter_chunk)

    def _call_gemini(self, prompt, system, chain, json_mode, max_tokens, temperature, images, max_retries, partial):
        parts = [{"text": prompt}]
        for img in images or []:
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(img).decode()}})
        contents = [{"role": "user", "parts": parts}]
        if partial:
            contents.append({"role": "model", "parts": [{"text": partial}]})
            contents.append({"role": "user", "parts": [{"text": CONTINUE_PROMPT}]})
        body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        if json_mode and not partial:
            body["generationConfig"]["responseMimeType"] = "application/json"
        # Key goes in a header, not the URL, so it never shows up in error messages or logs.
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        # Gemini has no server-side fallback, so the chain is walked here: one target per model.
        targets = [(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:streamGenerateContent?alt=sse", body, m) for m in chain]
        return self._post(targets, headers, max_retries, _gemini_chunk)

    def _read_stream(self, resp, read_chunk, label):
        """Collect an SSE stream. A drop after some text returns finish="length",
        so generate_text asks the model to continue from where it stopped."""
        text, finish, model, usage = [], None, None, {}
        # SSE is always UTF-8, but requests assumes ISO-8859-1 for text/* without a charset,
        # which turns Hindi, ₹, “quotes” etc. into mojibake like "à¤¶à¥".
        resp.encoding = "utf-8"
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue  # blank lines and keep-alive comments
                payload = line[len("data: "):]
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)
                if chunk.get("error"):
                    raise _StreamDropped(f"error mid-reply: {chunk['error']}")
                piece, chunk_finish, chunk_model, chunk_usage = read_chunk(chunk)
                text.append(piece)
                finish = chunk_finish or finish
                model = chunk_model or model
                usage = chunk_usage or usage
        except (requests.exceptions.RequestException, _StreamDropped) as e:
            if not "".join(text):
                raise _StreamDropped(str(e)[:300])
            print(f"[LLM] stream dropped after {len(''.join(text))} chars ({type(e).__name__}); will continue from there")
            return "".join(text), "length"
        print(f"[LLM] {model or label} tokens in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}"
              + (f" thinking={usage['thinking_tokens']}" if usage.get("thinking_tokens") else "")
              + (f" cost=${usage['cost']}" if "cost" in usage else ""))
        return "".join(text), finish

    def _post(self, targets, headers, max_retries, read_chunk):
        """POST to the first target; on busy/quota/retired-model errors move to the next model
        before waiting. Connection failures (request never ran) get CONNECT_RETRIES with growing
        waits; other failures get max_retries."""
        server_failures = connect_failures = rate_limited = 0
        i = 0
        while True:
            url, body, label = targets[i % len(targets)]
            host = url.split("/")[2]
            last_in_round = (i + 1) % len(targets) == 0
            started = time.time()
            try:
                # The read timeout is the longest silence between stream chunks, not the whole reply.
                resp = requests.post(url, json=body, headers=headers, timeout=(20, 300), verify=self.verify, stream=True)
                if resp.status_code == 200:
                    return self._read_stream(resp, read_chunk, label)
                err = LLMClientError(f"LLM request failed {resp.status_code} ({label}): {resp.text[:500]}")
                if resp.status_code in (404, 429, 500, 503) and not last_in_round:
                    print(f"[LLM] {label} returned {resp.status_code}; trying next model")
                    i += 1
                    continue
                i += 1
                # Bad key, no credits, bad model id, bad request: retrying will not help.
                if resp.status_code in (400, 401, 402, 403, 404):
                    raise err
                # Busy or out of quota on every model: a short wait usually clears it.
                if resp.status_code == 429 and rate_limited < 3:
                    rate_limited += 1
                    print(f"[LLM] rate-limited (429) on every model, waiting {15 * rate_limited}s")
                    time.sleep(15 * rate_limited)
                    continue
            except requests.exceptions.SSLError as e:
                raise LLMClientError(f"TLS verification failed; set CA_BUNDLE in .env to your system CA file. Details: {e}")
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
                connect_failures += 1
                wait = min(30, 2 ** connect_failures)
                print(f"[LLM] could not reach {host} (attempt {connect_failures}/{settings.CONNECT_RETRIES}, "
                      f"{time.time() - started:.1f}s): {type(e).__name__}; retrying in {wait}s")
                if connect_failures >= settings.CONNECT_RETRIES:
                    raise LLMClientError(f"Could not connect to {host} after {connect_failures} attempts. "
                                         f"Check your internet, VPN or proxy. Last error: {type(e).__name__}")
                time.sleep(wait)
                continue
            except requests.exceptions.ReadTimeout:
                err = LLMClientError(f"Model went silent for too long ({label})")
            except _StreamDropped as e:
                err = LLMClientError(f"Reply stream failed before any text arrived ({label}): {e}")
            server_failures += 1
            print(f"[LLM] attempt {server_failures}/{max_retries} failed: {str(err)[:200]}")
            if server_failures >= max_retries:
                raise err
            time.sleep(min(30, 3 * 2 ** server_failures))


CONTINUE_PROMPT = "You were cut off. Continue exactly from the last character above. Output only the remaining text, no repetition, no commentary."
