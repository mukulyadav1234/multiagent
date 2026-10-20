import json
import traceback
from .agents import AnalyzerAgent, CreativeDirectorAgent, CodeWriterAgent
from .services.artifact_service import create_generation_dir, save_html
from .scripts.render_poster import render_html_to_png_async
from pathlib import Path


class OrchestratorError(RuntimeError):
    pass


class Orchestrator:
    def __init__(self, llm_client=None):
        self.analyzer = AnalyzerAgent(llm=llm_client)
        self.creative = CreativeDirectorAgent(llm=llm_client)
        self.writer = CodeWriterAgent(llm=llm_client)

    async def generate(self, user_prompt: str, width: int = None, height: int = None, brand: str = None):
        gen_dir = create_generation_dir()
        try:
            analysis = self.analyzer.analyze(user_prompt)
            # apply overrides
            if width:
                analysis["width"] = width
            if height:
                analysis["height"] = height
            if brand:
                analysis["brand"] = brand

            creative = self.creative.decide(analysis)
            print("[ORCH] Creative JSON:", json.dumps(creative, indent=2, ensure_ascii=False))
            html = self.writer.write(analysis, creative)
            print("[ORCH] HTML generated length:", len(html))
            print("[ORCH] HTML preview:\n", html[:400])
            save_html(gen_dir, html)

            out_png = gen_dir / "poster.png"
            await render_html_to_png_async(
                html,
                out_png,
                int(analysis.get("width", 1080)),
                int(analysis.get("height", 1350)),
                format="png",
            )

            return {"generation_id": gen_dir.name, "analysis": analysis, "creative": creative, "html": html}
        except Exception as e:
            traceback.print_exc()
            raise OrchestratorError(str(e))
