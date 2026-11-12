import asyncio
import json
import pytest
from backend.orchestrator import Orchestrator, OrchestratorError
from backend.llm_client import parse_json_object, LLMClientError
from backend.agents.code_writer import extract_html
from backend.services import artifact_service

HTML = '<!doctype html><html><body><div id="poster" style="width:1080px;height:1350px"></div><script>window.__POSTER_READY=true</script></body></html>'


class DummyLLM:
    def __init__(self, review_pass=True, brand="Unknown Brand"):
        self.calls = []
        self.review_pass = review_pass
        self.brand = brand

    def generate_text(self, prompt, system=None, model=None, json_mode=False, max_output_tokens=4000, temperature=0.7, images=None, **kw):
        role = system.split("\n", 1)[0]
        self.calls.append(role)
        if "Brief Agent" in role:
            return json.dumps({"title": "Leopard", "subject": "snow leopard", "brand": self.brand, "include_text": False, "width": 5000, "height": 1350})
        if "Creative Director" in role:
            return '```json\n' + json.dumps({"concept_name": "Ridge", "text_blocks": [{"role": "brand", "text": "X"}], "canvas": {"width": 1, "height": 1}}) + '\n```'
        if "art director doing quality control" in role:
            assert images, "reviewer must receive the rendered image"
            return json.dumps({"score": 9 if self.review_pass else 5, "pass": self.review_pass, "summary": "ok", "issues": [] if self.review_pass else [{"severity": "high", "area": "subject", "problem": "flat", "fix": "shade it"}]})
        return "Here you go:\n```html\n" + HTML + "\n```"


@pytest.fixture(autouse=True)
def isolated_outputs(tmp_path, monkeypatch):
    # Keep test generations out of the real outputs/ folder.
    monkeypatch.setattr(artifact_service, "ROOT", tmp_path)


@pytest.fixture
def fake_render(monkeypatch):
    async def render(html, out_path, w, h, format="png", scale=2):
        out_path.write_bytes(b"\x89PNG fake")
        return []
    monkeypatch.setattr("backend.scripts.render_poster.render_html_to_png_async", render)


def test_any_prompt_without_company(fake_render):
    llm = DummyLLM()
    res = asyncio.run(Orchestrator(llm_client=llm).generate("A photorealistic snow leopard at golden hour"))
    assert res["analysis"]["brand"] is None
    assert res["analysis"]["width"] == 2400  # clamped
    assert res["creative"]["canvas"] == {"width": 2400, "height": 1350}
    assert res["creative"]["text_blocks"] == []  # no brand block without a brand
    assert res["html"].startswith("<!doctype html>") and res["html"].endswith("</html>")


def test_failed_review_triggers_revision(fake_render, monkeypatch):
    monkeypatch.setattr("backend.config.settings.REVIEW_ROUNDS", 1)
    llm = DummyLLM(review_pass=False)
    asyncio.run(Orchestrator(llm_client=llm).generate("Diwali poster"))
    # brief, director, writer, reviewer, writer (revision)
    assert len(llm.calls) == 5
    assert "creative coder" in llm.calls[-1]


def test_explicit_size_and_brand_win(fake_render):
    res = asyncio.run(Orchestrator(llm_client=DummyLLM()).generate("poster", width=1080, height=1080, brand="NIIT"))
    assert (res["width"], res["height"], res["analysis"]["brand"]) == (1080, 1080, "NIIT")


def test_parse_json_object_handles_fences_and_chatter():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! {"a": 2} hope this helps') == {"a": 2}
    with pytest.raises(LLMClientError):
        parse_json_object("no json here")


def test_extract_html_rejects_truncated_output():
    assert extract_html("```html\n" + HTML + "\n```") == HTML
    with pytest.raises(LLMClientError):
        extract_html("<!doctype html><html><body><svg>")


def test_artifact_path_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(artifact_service, "ROOT", tmp_path)
    (tmp_path / "abc").mkdir()
    (tmp_path / "abc" / "poster.png").write_bytes(b"x")
    (tmp_path / "secret.env").write_text("KEY=1")
    assert artifact_service.get_artifact_path("abc", "poster.png") is not None
    assert artifact_service.get_artifact_path("abc", "../secret.env") is None
    assert artifact_service.get_artifact_path("..", "secret.env") is None


class FakeResp:
    def __init__(self, status, data, drop_after=None):
        self.status_code, self._data, self.text = status, data, json.dumps(data)
        self.drop_after = drop_after

    def json(self):
        return self._data

    def iter_lines(self, decode_unicode=False):
        """Serve the reply as an OpenRouter SSE stream, one character per chunk."""
        import requests
        yield ": OPENROUTER PROCESSING"
        choice = self._data["choices"][0]
        for i, ch in enumerate(choice["message"]["content"]):
            if self.drop_after is not None and i == self.drop_after:
                raise requests.exceptions.ChunkedEncodingError("proxy cut the connection")
            yield "data: " + json.dumps({"choices": [{"delta": {"content": ch}}]})
        yield "data: " + json.dumps({"model": "m", "choices": [{"delta": {}, "finish_reason": choice["finish_reason"]}], "usage": {"completion_tokens": 1}})
        yield "data: [DONE]"


OK_REPLY = {"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]}


def _client(monkeypatch, responses):
    import requests
    from backend.llm_client import LLMClient
    calls = []

    def post(*a, **kw):
        calls.append(1)
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr("backend.llm_client.time.sleep", lambda s: None)
    return LLMClient(api_key="test", provider="openrouter"), calls


def test_connect_timeouts_are_retried(monkeypatch):
    import requests
    client, calls = _client(monkeypatch, [requests.exceptions.ConnectTimeout("t"), requests.exceptions.ConnectionError("c"), FakeResp(200, OK_REPLY)])
    assert client.generate_text("x", max_retries=1) == "hi"
    assert len(calls) == 3


def test_connect_retries_give_up_with_clear_message(monkeypatch):
    import requests
    client, calls = _client(monkeypatch, [requests.exceptions.ConnectTimeout("t")] * 10)
    with pytest.raises(LLMClientError, match="Could not connect to openrouter.ai"):
        client.generate_text("x")
    assert len(calls) == 6


def test_no_credits_is_not_retried(monkeypatch):
    client, calls = _client(monkeypatch, [FakeResp(402, {"error": "credits"})] * 3)
    with pytest.raises(LLMClientError, match="402"):
        client.generate_text("x")
    assert len(calls) == 1


def test_model_list_becomes_fallback_chain(monkeypatch):
    import requests
    from backend.llm_client import LLMClient
    sent = []
    monkeypatch.setattr(requests, "post", lambda *a, **kw: sent.append(kw["json"]) or FakeResp(200, OK_REPLY))
    client = LLMClient(api_key="test", provider="openrouter")
    client.generate_text("x", model="a/one:free, b/two:free")
    client.generate_text("x", model="a/one")
    assert sent[0]["models"] == ["a/one:free", "b/two:free"] and "model" not in sent[0]
    assert sent[1]["model"] == "a/one" and "models" not in sent[1]


def test_rate_limit_waits_then_succeeds(monkeypatch):
    client, calls = _client(monkeypatch, [FakeResp(429, {}), FakeResp(429, {}), FakeResp(200, OK_REPLY)])
    assert client.generate_text("x", max_retries=1) == "hi"
    assert len(calls) == 3


def test_dropped_stream_keeps_text_and_continues(monkeypatch):
    first = FakeResp(200, {"choices": [{"message": {"content": "<html>abc"}, "finish_reason": "stop"}]}, drop_after=6)
    rest = FakeResp(200, {"choices": [{"message": {"content": "abc</html>"}, "finish_reason": "stop"}]})
    client, calls = _client(monkeypatch, [first, rest])
    assert client.generate_text("x") == "<html>abc</html>"
    assert len(calls) == 2


def test_stream_drop_before_any_text_is_retried(monkeypatch):
    client, calls = _client(monkeypatch, [FakeResp(200, OK_REPLY, drop_after=0), FakeResp(200, OK_REPLY)])
    assert client.generate_text("x", max_retries=2) == "hi"
    assert len(calls) == 2


class FakeGeminiResp(FakeResp):
    def iter_lines(self, decode_unicode=False):
        text = self._data["choices"][0]["message"]["content"]
        yield "data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True}]}}]})
        yield "data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
                                     "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1}, "modelVersion": "g"})


def test_gemini_walks_fallback_chain(monkeypatch):
    import requests
    from backend.llm_client import LLMClient
    urls = []
    replies = [FakeResp(503, {"error": "busy"}), FakeResp(429, {"error": "quota"}), FakeGeminiResp(200, OK_REPLY)]
    monkeypatch.setattr(requests, "post", lambda url, **kw: urls.append(url) or replies.pop(0))
    client = LLMClient(api_key="test", provider="gemini")
    assert client.generate_text("x", model="m-one, m-two, m-three") == "hi"  # thought parts are dropped
    assert [u.split("/models/")[1].split(":")[0] for u in urls] == ["m-one", "m-two", "m-three"]


def test_model_for_follows_provider(monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    assert settings.model_for("coder") == settings.GEMINI_MODEL_CODER
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openrouter")
    assert settings.model_for("coder") == settings.MODEL_CODER


def test_stream_keeps_non_english_text(monkeypatch):
    """Real requests.Response, so the ISO-8859-1 default for text/event-stream applies."""
    import io
    import requests
    from requests.utils import get_encoding_from_headers
    from backend.llm_client import LLMClient

    text = "शुभ दीपावली ₹499 “Sale” — café"
    sse = "".join("data: " + json.dumps({"choices": [{"delta": {"content": ch}}]}, ensure_ascii=False) + "\n\n" for ch in text)
    sse += "data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\ndata: [DONE]\n\n"

    def post(*a, **kw):
        resp = requests.models.Response()
        resp.status_code = 200
        resp.headers["content-type"] = "text/event-stream"
        resp.encoding = get_encoding_from_headers(resp.headers)  # what requests' adapter does
        resp.raw = io.BytesIO(sse.encode("utf-8"))
        return resp
    monkeypatch.setattr(requests, "post", post)
    assert LLMClient(api_key="test", provider="openrouter").generate_text("x") == text


def test_status_after_backend_restart(tmp_path):
    """Jobs live in memory; after a restart the status endpoint must explain, not 404."""
    from fastapi import HTTPException
    from backend import main
    main.JOBS.clear()  # simulate a fresh process
    status = lambda gid: asyncio.run(main.generation_status(gid))

    (tmp_path / "interrupted").mkdir()  # job folder made, then the backend restarted
    r = status("interrupted")
    assert r["status"] == "error" and "backend restarted" in r["error"]

    (tmp_path / "failed").mkdir()
    (tmp_path / "failed" / "status.json").write_text(json.dumps({"status": "error", "stage": "x", "error": "402 no credits"}))
    assert status("failed")["error"] == "402 no credits"

    for missing in ("does-not-exist", ".."):
        with pytest.raises(HTTPException) as e:
            status(missing)
        assert e.value.status_code == 404
