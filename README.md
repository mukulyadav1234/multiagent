# AI Poster Studio

Local app that turns any text request into a high-resolution image, using only text-to-text models: the models write HTML + inline SVG + CSS, and Chromium renders it.

Pipeline (prompts in `prompts/`)
1. **Brief** (`analyzer.txt`): any request, even one word, -> structured brief. Never asks for a company or other details.
2. **Creative Director** (`creative_director.txt`): brief -> layered shot plan (lighting, depth planes, materials, typography).
3. **Code Writer** (`code_writer.txt`): plan -> HTML/SVG painting, using a realism toolkit (gradient shading, SVG lighting/turbulence filters, bloom, depth of field, grain, seeded procedural scripts, Google Fonts).
4. **Compile**: render with Playwright, a vision **Reviewer** (`reviewer.txt`) critiques the PNG, the Code Writer revises (`REVIEW_ROUNDS`), then the final render.

Output: PNG at 2x or 4x pixel density (1080x1350 -> 4320x5400), JPG, vector PDF, and the HTML source.

Provider: Gemini by default (`GEMINI_API_KEY`), one model chain per agent via `GEMINI_MODEL_*` in `.env`. Set `LLM_PROVIDER=openrouter` to use OpenRouter instead (`MODEL_*`). All calls are streamed and fall through a model chain when one model is busy or out of quota.

Quick setup (Linux)

1. Create and activate a Python venv
```bash
python3 -m venv .venv
source .venv/bin/activate
```
2. Install Python dependencies
```bash
pip install -r requirements.txt
```
3. Install Playwright browsers
```bash
playwright install chromium
```
4. Configure `.env` (copy `.env.example`)
5. Start backend
```bash
uvicorn backend.main:app --reload --port 8000
```
6. Start frontend (from `frontend/`)
```bash
cd frontend
npm install
npm run dev
```

Notes
- A generation makes 4-5 model calls and takes roughly 2-5 minutes; the UI polls `/api/generations/{id}` and shows the current stage.
- Renders are sandboxed: only Google Fonts may load.
- Tests in `tests/` mock the LLM and renderer: `pytest -q`.
