# AI Marketing Studio

Minimal local app that generates marketing posters using a three-agent pipeline and Google Gemini (text) + Playwright HTML rendering.

Overview
- Backend: FastAPI (Python)
- Frontend: Vite + React (minimal scaffold)
- Agents: Analyzer, Creative Director, Code Writer (prompts in `prompts/`)
- Rendering: Playwright + Chromium (render HTML to PNG/JPEG/PDF)

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
- The code includes a small Gemini client wrapper that attempts to call the Generative REST endpoint. Verify your API key and model.
- Tests exist in `tests/` and mock the LLM where appropriate.
