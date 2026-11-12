import asyncio
import json
import traceback
from typing import Callable, Optional
from .agents import AnalyzerAgent, CreativeDirectorAgent, CodeWriterAgent, ReviewerAgent
from .services.artifact_service import create_generation_dir, save_html
from .scripts import render_poster
from .config import settings


class OrchestratorError(RuntimeError):
    pass


class Orchestrator:
    """Brief -> Creative Director -> Code Writer -> compile (render, review, revise)."""

    def __init__(self, llm_client=None):
        self.analyzer = AnalyzerAgent(llm=llm_client)
        self.creative = CreativeDirectorAgent(llm=llm_client)
        self.writer = CodeWriterAgent(llm=llm_client)
        self.reviewer = ReviewerAgent(llm=llm_client)

    async def generate(self, user_prompt: str, width: int = None, height: int = None, brand: str = None,
                       gen_dir=None, on_stage: Optional[Callable[[str], None]] = None):
        gen_dir = gen_dir or create_generation_dir()
        stage = on_stage or (lambda s: print("[ORCH]", s))
        try:
            stage("Reading your request")
            analysis = await asyncio.to_thread(self.analyzer.analyze, user_prompt, width, height, brand)
            w, h = analysis["width"], analysis["height"]

            stage("Planning the shot: lighting, depth, materials")
            creative = await asyncio.to_thread(self.creative.decide, analysis)

            stage("Painting the image in SVG/HTML")
            html = await asyncio.to_thread(self.writer.write, analysis, creative)
            save_html(gen_dir, html, "draft_1.html")

            reviews = []
            for round_no in range(1, settings.REVIEW_ROUNDS + 1):
                stage(f"Compiling and reviewing (round {round_no})")
                review_png = gen_dir / f"review_{round_no}.png"
                errors = await render_poster.render_html_to_png_async(html, review_png, w, h, format="png", scale=1)
                try:
                    review = await asyncio.to_thread(self.reviewer.review, analysis, creative, review_png.read_bytes(), errors)
                except Exception as e:
                    # A model without image input should not sink the whole generation.
                    print("[ORCH] Review skipped:", repr(e))
                    reviews.append({"skipped": str(e)[:300]})
                    break
                reviews.append(review)
                if review["pass"]:
                    break
                stage(f"Fixing {len(review['issues'])} review notes")
                try:
                    html = await asyncio.to_thread(self.writer.revise, analysis, creative, html, review["issues"], errors)
                    save_html(gen_dir, html, f"draft_{round_no + 1}.html")
                except Exception as e:
                    print("[ORCH] Revision failed, keeping previous draft:", repr(e))
                    reviews.append({"revision_failed": str(e)[:300]})
                    break

            stage("Rendering final high-resolution image")
            save_html(gen_dir, html)
            errors = await render_poster.render_html_to_png_async(html, gen_dir / "poster.png", w, h, format="png", scale=settings.PREVIEW_SCALE)

            result = {"generation_id": gen_dir.name, "prompt": user_prompt, "analysis": analysis, "creative": creative,
                      "reviews": reviews, "console_errors": errors, "width": w, "height": h}
            (gen_dir / "meta.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            return {**result, "html": html}
        except Exception as e:
            traceback.print_exc()
            raise OrchestratorError(str(e))
