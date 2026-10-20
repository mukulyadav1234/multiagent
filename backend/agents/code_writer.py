from typing import Dict
from ..llm_client import LLMClient, LLMClientError
from pathlib import Path
from ..config import settings


class CodeWriterAgent:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
        p = Path(__file__).resolve().parents[2] / "prompts/code_writer.txt"
        self.prompt_text = p.read_text()

    def _fallback_html(self, analysis: Dict, creative: Dict) -> str:
        width = int(analysis.get("width", 1080))
        height = int(analysis.get("height", 1350))
        brand = str(creative.get("brand") or analysis.get("brand") or "Brand")
        headline = str(creative.get("headline") or "HAPPY HOLI")
        subheadline = str(creative.get("subheadline") or "May your world be filled with colour, joy and new beginnings.")
        footer = str(creative.get("footer") or f"{brand} celebrates colour and community")
        occasion = str(analysis.get("occasion", "")).lower()

        if "ai" in occasion or "technology" in occasion or "event" in occasion:
            bg1, bg2, accent1, accent2, accent3 = "#0F172A", "#111827", "#67E8F9", "#8B5CF6", "#F8FAFC"
            return f'''
            <!doctype html>
            <html lang="en">
            <head>
              <meta charset="utf-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1" />
              <title>{headline}</title>
              <style>
                * {{ box-sizing: border-box; }}
                html, body {{ margin: 0; padding: 0; background: #050b14; font-family: Arial, sans-serif; }}
                body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
                .poster {{ position: relative; width: {width}px; height: {height}px; overflow: hidden; background: linear-gradient(180deg, {bg1} 0%, {bg2} 100%); border-radius: 26px; box-shadow: 0 30px 80px rgba(0,0,0,0.28); }}
                .grid {{ position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px); background-size: 32px 32px; mask-image: radial-gradient(circle at center, black 40%, transparent 100%); }}
                .node {{ position: absolute; border-radius: 14px; background: rgba(103,232,249,0.15); border: 1px solid rgba(103,232,249,0.3); box-shadow: 0 0 20px rgba(103,232,249,0.2); }}
                .brand {{ position: absolute; top: 26px; left: 42px; font-weight: 800; font-size: 26px; letter-spacing: 3px; color: {accent3}; text-transform: uppercase; }}
                .content {{ position: absolute; left: 42px; top: 110px; width: 60%; z-index: 4; }}
                h1 {{ margin: 0; font-size: 88px; line-height: 0.9; letter-spacing: -3px; font-weight: 900; color: {accent3}; text-transform: uppercase; }}
                .sub {{ margin-top: 22px; width: 84%; font-size: 25px; line-height: 1.45; color: rgba(255,255,255,0.8); }}
                .signal {{ position: absolute; right: -120px; top: 210px; width: 690px; height: 690px; border-radius: 28px; border: 1px solid rgba(139,92,246,0.3); background: radial-gradient(circle at center, rgba(103,232,249,0.18), rgba(139,92,246,0.08) 35%, transparent 70%); transform: rotate(18deg); }}
                .pill {{ position: absolute; right: 90px; bottom: 100px; width: 270px; height: 150px; border-radius: 18px; background: linear-gradient(135deg, rgba(103,232,249,0.18), rgba(139,92,246,0.26)); border: 1px solid rgba(255,255,255,0.13); box-shadow: 0 0 40px rgba(103,232,249,0.12); }}
                .footer {{ position: absolute; left: 42px; right: 42px; bottom: 30px; display: flex; justify-content: space-between; align-items: center; color: rgba(255,255,255,0.8); font-size: 18px; }}
                .tag {{ font-weight: 700; color: {accent1}; }}
              </style>
            </head>
            <body>
              <div class="poster">
                <div class="grid"></div>
                <div class="signal"></div>
                <div class="node" style="left: 72px; top: 430px; width: 140px; height: 100px;"></div>
                <div class="node" style="right: 180px; top: 220px; width: 180px; height: 120px;"></div>
                <div class="node" style="left: 250px; bottom: 150px; width: 220px; height: 90px;"></div>
                <div class="brand">{brand}</div>
                <div class="content">
                  <h1>{headline}</h1>
                  <div class="sub">{subheadline}</div>
                </div>
                <div class="pill"></div>
                <div class="footer">
                  <span class="tag">{brand}</span>
                  <span>{footer}</span>
                </div>
              </div>
            </body>
            </html>
            '''

        if "recruit" in occasion or "career" in occasion or "job" in occasion:
            bg1, bg2, accent1, accent2, accent3 = "#F8FAFC", "#E2E8F0", "#2563EB", "#0F172A", "#475569"
            return f'''
            <!doctype html>
            <html lang="en">
            <head>
              <meta charset="utf-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1" />
              <title>{headline}</title>
              <style>
                * {{ box-sizing: border-box; }}
                html, body {{ margin: 0; padding: 0; background: #eef3f8; font-family: Arial, sans-serif; }}
                body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
                .poster {{ position: relative; width: {width}px; height: {height}px; overflow: hidden; background: linear-gradient(180deg, {bg1} 0%, {bg2} 100%); border-radius: 24px; box-shadow: 0 24px 70px rgba(15,23,42,0.18); }}
                .panel {{ position: absolute; right: 80px; top: 110px; width: 360px; height: 760px; border-radius: 26px; background: linear-gradient(180deg, rgba(37,99,235,0.12), rgba(15,23,42,0.04)); border: 1px solid rgba(15,23,42,0.12); }}
                .portrait {{ position: absolute; right: 120px; top: 220px; width: 260px; height: 380px; border-radius: 32px 32px 18px 18px; background: linear-gradient(180deg, #dfe7f4 0%, #bfcfe7 100%); box-shadow: inset 0 0 0 14px rgba(255,255,255,0.4); }}
                .head {{ position: absolute; right: 205px; top: 260px; width: 90px; height: 90px; border-radius: 50%; background: #f3d2b0; }}
                .body {{ position: absolute; right: 165px; top: 360px; width: 170px; height: 180px; border-radius: 22px 22px 32px 32px; background: #1d4ed8; }}
                .brand {{ position: absolute; left: 42px; top: 30px; font-size: 26px; font-weight: 800; letter-spacing: 3px; color: {accent2}; text-transform: uppercase; }}
                .content {{ position: absolute; left: 42px; top: 110px; width: 58%; }}
                h1 {{ margin: 0; font-size: 78px; line-height: 0.94; letter-spacing: -2.5px; font-weight: 900; color: {accent2}; }}
                .sub {{ margin-top: 18px; font-size: 24px; line-height: 1.4; color: {accent3}; width: 88%; }}
                .cta {{ position: absolute; left: 42px; bottom: 58px; padding: 14px 24px; border-radius: 999px; background: {accent1}; color: white; font-weight: 800; letter-spacing: 1px; }}
                .footer {{ position: absolute; left: 42px; right: 42px; bottom: 26px; display: flex; justify-content: space-between; color: {accent3}; font-size: 17px; }}
              </style>
            </head>
            <body>
              <div class="poster">
                <div class="brand">{brand}</div>
                <div class="content">
                  <h1>{headline}</h1>
                  <div class="sub">{subheadline}</div>
                </div>
                <div class="panel"></div>
                <div class="portrait"></div>
                <div class="head"></div>
                <div class="body"></div>
                <div class="cta">APPLY NOW</div>
                <div class="footer">
                  <span>{brand}</span>
                  <span>{footer}</span>
                </div>
              </div>
            </body>
            </html>
            '''

        gradient1, gradient2, pink, orange, yellow, cyan, purple = "#FF5BAA", "#FF8E3C", "#FF4DA6", "#FF8A00", "#FDE047", "#33D4FF", "#7C4DFF"
        return f'''
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>{headline}</title>
          <style>
            * {{ box-sizing: border-box; }}
            html, body {{ margin: 0; padding: 0; background: #faf1f6; font-family: Arial, sans-serif; }}
            body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
            .poster {{ position: relative; width: {width}px; height: {height}px; overflow: hidden; background: linear-gradient(180deg, {gradient1} 0%, {gradient2} 38%, #ffd86b 100%); border-radius: 28px; box-shadow: 0 30px 80px rgba(0,0,0,0.22); }}
            .cloud {{ position: absolute; border-radius: 50%; filter: blur(1px); opacity: 0.94; }}
            .powder {{ position: absolute; border-radius: 50%; filter: blur(2px); opacity: 0.9; }}
            .spark {{ position: absolute; width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.8); box-shadow: 0 0 18px rgba(255,255,255,0.8); }}
            .brand {{ position: absolute; left: 46px; top: 30px; z-index: 10; font-size: 26px; font-weight: 800; letter-spacing: 3px; color: rgba(255,255,255,0.94); text-transform: uppercase; }}
            .content {{ position: absolute; left: 48px; top: 110px; width: 70%; z-index: 10; }}
            h1 {{ margin: 0; font-size: 110px; line-height: 0.85; letter-spacing: -3px; font-weight: 900; color: #fffaf6; text-transform: uppercase; text-shadow: 0 18px 32px rgba(0,0,0,0.12); }}
            .sub {{ margin-top: 18px; font-size: 28px; line-height: 1.45; color: rgba(255,255,255,0.92); width: 72%; }}
            .footer {{ position: absolute; left: 48px; right: 48px; bottom: 28px; display: flex; justify-content: space-between; align-items: center; z-index: 12; }}
            .footer .brand-tag {{ font-weight: 800; letter-spacing: 2px; color: #fffaf6; font-size: 26px; }}
            .footer .small {{ font-size: 18px; color: rgba(255,255,255,0.9); }}
          </style>
        </head>
        <body>
          <div class="poster">
            <div class="cloud" style="left: -60px; top: 80px; width: 360px; height: 210px; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.45), {pink} 18%, rgba(255,103,165,0.9) 44%, rgba(255,103,165,0.18) 72%, transparent 100%);"></div>
            <div class="cloud" style="right: -50px; top: 100px; width: 420px; height: 230px; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.4), {orange} 18%, rgba(255,147,62,0.9) 42%, rgba(255,147,62,0.18) 74%, transparent 100%);"></div>
            <div class="cloud" style="left: 180px; top: 210px; width: 520px; height: 300px; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.38), {pink} 18%, rgba(255,100,170,0.9) 44%, rgba(255,100,170,0.2) 75%, transparent 100%);"></div>
            <div class="cloud" style="right: 90px; top: 300px; width: 400px; height: 220px; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.38), {cyan} 18%, rgba(75,212,255,0.82) 42%, rgba(75,212,255,0.18) 74%, transparent 100%);"></div>
            <div class="cloud" style="left: 90px; top: 430px; width: 350px; height: 200px; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.34), {yellow} 18%, rgba(255,214,73,0.84) 42%, rgba(255,214,73,0.18) 75%, transparent 100%);"></div>
            <div class="cloud" style="right: 150px; top: 500px; width: 360px; height: 200px; background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.34), {purple} 18%, rgba(126,99,255,0.85) 42%, rgba(126,99,255,0.18) 75%, transparent 100%);"></div>

            <div class="powder" style="left: 120px; top: 230px; width: 170px; height: 170px; background: radial-gradient(circle, rgba(255,255,255,0.35), {pink} 18%, rgba(255,122,172,0.9) 42%, transparent 76%);"></div>
            <div class="powder" style="right: 90px; top: 220px; width: 190px; height: 190px; background: radial-gradient(circle, rgba(255,255,255,0.35), {yellow} 18%, rgba(255,200,66,0.9) 42%, transparent 76%);"></div>
            <div class="powder" style="left: 340px; top: 520px; width: 230px; height: 220px; background: radial-gradient(circle, rgba(255,255,255,0.32), {cyan} 22%, rgba(88,214,255,0.9) 46%, transparent 80%);"></div>
            <div class="powder" style="right: 250px; top: 580px; width: 220px; height: 200px; background: radial-gradient(circle, rgba(255,255,255,0.32), {purple} 18%, rgba(128,103,255,0.9) 44%, transparent 80%);"></div>

            <div class="spark" style="left: 180px; top: 210px;"></div>
            <div class="spark" style="left: 530px; top: 210px;"></div>
            <div class="spark" style="left: 680px; top: 500px;"></div>
            <div class="spark" style="left: 310px; top: 760px;"></div>
            <div class="spark" style="left: 820px; top: 760px;"></div>
            <div class="spark" style="left: 920px; top: 420px;"></div>
            <div class="spark" style="left: 180px; top: 620px;"></div>
            <div class="spark" style="left: 860px; top: 240px;"></div>

            <div class="brand">{brand}</div>

            <div class="content">
              <h1>{headline}</h1>
              <div class="sub">{subheadline}</div>
            </div>

            <div class="footer">
              <div class="brand-tag">{brand}</div>
              <div class="small">{footer}</div>
            </div>
          </div>
        </body>
        </html>
        '''

    def write(self, analysis: Dict, creative: Dict, retries: int = 1) -> str:
        prompt = self.prompt_text + "\nAnalyzer JSON:\n" + str(analysis) + "\nCreative JSON:\n" + str(creative)
        print("[AGENT] Code Writer prompt:\n", prompt)
        try:
            out = self.llm.generate_text(
                prompt,
                max_retries=retries or settings.MAX_AGENT_RETRIES,
                response_mime_type="text/html",
                max_output_tokens=1800,
            )
            print("[AGENT] Code Writer raw output start")
            print(out[:1500])
            print("[AGENT] Code Writer raw output end")
            if not out:
                print("[AGENT] Code Writer: LLM returned empty HTML, using fallback template")
                return self._fallback_html(analysis, creative)

            cleaned = out.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```html", "").replace("```", "").strip()
            if "<html" in cleaned.lower() or "<!doctype" in cleaned.lower():
                start = cleaned.lower().find("<html")
                if start == -1:
                    start = cleaned.lower().find("<!doctype")
                if start != -1:
                    return cleaned[start:]
            print("[AGENT] Code Writer: malformed or non-HTML response, using fallback template")
            return self._fallback_html(analysis, creative)
        except Exception as exc:
            print("[AGENT] Code Writer exception:", repr(exc))
            return self._fallback_html(analysis, creative)
