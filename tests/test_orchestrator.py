import asyncio
import pytest
from backend.orchestrator import Orchestrator, OrchestratorError
from backend.agents.creative_director import CreativeDirectorAgent


class DummyLLM:
    def generate_text(self, prompt, max_retries=1, response_mime_type=None, max_output_tokens=800):
        # Very naive deterministic responses for testing
        if 'analyzer' in prompt.lower() or 'Analyzer JSON' in prompt:
            return '{"brand":"NIIT","occasion":"Diwali","audience":"Professional","platform":"LinkedIn","width":1080,"height":1350,"tone":"Premium and festive","requirements":["Happy Diwali headline","Corporate greeting"]}'
        if 'creative' in prompt.lower() or 'Creative JSON' in prompt:
            return '{"headline":"Happy Diwali","subheadline":"Wishing you a bright year","brand":"NIIT","palette":["#10182B","#D4AF67","#FFF5DF"],"layout":"Centered premium","elements":["diyas","gold accents"],"footer":"Warm wishes from NIIT"}'
        if 'code_writer' in prompt.lower() or '<html' in prompt.lower():
            return '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}</style></head><body><div style="width:1080px;height:1350px;background:#10182B;color:#fff;display:flex;align-items:center;justify-content:center;font-family:Arial"><h1>Happy Diwali - NIIT</h1></div></body></html>'
        return '{}'


def test_full_generation(tmp_path, monkeypatch):
    # Use dummy LLM to avoid real API calls
    monkeypatch.setattr('backend.scripts.render_poster.render_html_to_png_async', lambda html, out_path, w, h, format='png': None)
    ork = Orchestrator(llm_client=DummyLLM())
    res = asyncio.run(ork.generate('Create a Happy Diwali poster for NIIT'))
    assert 'generation_id' in res
    assert res['analysis']['brand'] == 'NIIT'
    assert '<html' in res['html'].lower()


def test_creative_fallback_is_campaign_specific():
    agent = CreativeDirectorAgent(llm=DummyLLM())

    holi = agent._fallback_creative({"brand": "NGY", "occasion": "Holi"})
    ai = agent._fallback_creative({"brand": "NovaLabs", "occasion": "AI event"})
    recruit = agent._fallback_creative({"brand": "VeloHire", "occasion": "Recruitment"})

    assert holi["headline"] == "HAPPY HOLI"
    assert ai["headline"] == "NEXT-GEN AI"
    assert recruit["headline"] == "JOIN OUR TEAM"

    assert holi["palette"][0] == "#FF5CA8"
    assert ai["palette"][0] == "#0F172A"
    assert recruit["palette"][0] == "#0F172A"
