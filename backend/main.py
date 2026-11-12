import asyncio
import json
import traceback
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .models.schemas import GenerateRequest, RecompileRequest
from .orchestrator import Orchestrator, OrchestratorError
from .services.artifact_service import create_generation_dir, get_artifact_path, get_generation_dir, save_html
from .scripts import render_poster
from .config import settings


app = FastAPI(title="AI Poster Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orch = Orchestrator()
# In-memory job table; generation takes minutes, so the UI polls instead of holding one request open.
JOBS = {}


def _load_meta(generation_id: str) -> dict:
    path = get_artifact_path(generation_id, "meta.json")
    if path is None:
        raise HTTPException(status_code=404, detail="generation id not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Describe the image you want.")
    gen_dir = create_generation_dir()
    job = {"status": "running", "stage": "Queued", "error": None}
    JOBS[gen_dir.name] = job

    def update(**fields):
        job.update(fields)
        # Mirrored to disk so a backend restart can still report what happened to this job.
        status = {k: job[k] for k in ("status", "stage", "error")}
        (gen_dir / "status.json").write_text(json.dumps({**status, "prompt": req.prompt}, ensure_ascii=False), encoding="utf-8")

    def on_stage(s):
        print("[ORCH]", s)
        update(stage=s)

    async def run():
        try:
            res = await orch.generate(req.prompt, width=req.width, height=req.height, brand=req.brand, gen_dir=gen_dir, on_stage=on_stage)
            update(status="done", stage="Done", result=res)
        except OrchestratorError as e:
            update(status="error", error=str(e))
        except Exception as e:
            traceback.print_exc()
            update(status="error", error=str(e))

    update()
    job["task"] = asyncio.create_task(run())
    return {"generation_id": gen_dir.name}


@app.get("/api/generations/{generation_id}")
async def generation_status(generation_id: str):
    job = JOBS.get(generation_id)
    if job is None:
        # Not running in this process: finished earlier, failed earlier, or cut off by a restart.
        if get_artifact_path(generation_id, "meta.json"):
            meta = _load_meta(generation_id)
            html_path = get_artifact_path(generation_id, "poster.html")
            return {"status": "done", "stage": "Done", "result": {**meta, "html": html_path.read_text(encoding="utf-8") if html_path else ""}}
        status_path = get_artifact_path(generation_id, "status.json")
        saved = json.loads(status_path.read_text(encoding="utf-8")) if status_path else {}
        if saved.get("status") == "error":
            return {"status": "error", "stage": saved.get("stage"), "error": saved.get("error")}
        if get_generation_dir(generation_id):
            return {"status": "error", "stage": saved.get("stage"),
                    "error": "This generation was interrupted because the backend restarted. Please click Generate again."}
        raise HTTPException(status_code=404, detail="generation id not found")
    out = {"status": job["status"], "stage": job["stage"], "error": job["error"]}
    if job["status"] == "done":
        out["result"] = job["result"]
    return JSONResponse(out)


@app.post("/api/recompile")
async def recompile(req: RecompileRequest):
    meta = _load_meta(req.generation_id)
    gen_dir = get_artifact_path(req.generation_id, "meta.json").parent
    original = gen_dir / "poster_original.html"
    current = gen_dir / "poster.html"
    if not original.exists() and current.exists():
        original.write_text(current.read_text(encoding="utf-8"), encoding="utf-8")
    save_html(gen_dir, req.html)
    # Drop cached exports so downloads reflect the edit.
    for old in [*gen_dir.glob("poster@*"), gen_dir / "poster.pdf"]:
        old.unlink(missing_ok=True)

    try:
        errors = await render_poster.render_html_to_png_async(req.html, gen_dir / "poster.png", meta["width"], meta["height"], format="png", scale=settings.PREVIEW_SCALE)
        return {"generation_id": req.generation_id, "preview_url": f"/api/artifacts/{req.generation_id}/preview", "console_errors": errors}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/artifacts/{generation_id}/preview")
async def preview(generation_id: str):
    path = get_artifact_path(generation_id, "poster.png")
    if path is None:
        raise HTTPException(status_code=404, detail="preview not found")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@app.get("/api/artifacts/{generation_id}/export")
async def export(generation_id: str, format: str = Query("png", pattern="^(png|jpeg|pdf)$"), scale: int = Query(2, ge=1, le=4)):
    """Re-render the current HTML at the requested pixel density. PDF stays vector at any zoom."""
    meta = _load_meta(generation_id)
    html_path = get_artifact_path(generation_id, "poster.html")
    if html_path is None:
        raise HTTPException(status_code=404, detail="source not found")
    ext = "jpg" if format == "jpeg" else format
    name = f"poster.{ext}" if format == "pdf" else f"poster@{scale}x.{ext}"
    out = html_path.parent / name
    if not out.exists():
        await render_poster.render_html_to_png_async(html_path.read_text(encoding="utf-8"), out, meta["width"], meta["height"], format=format, scale=scale)
    download_name = f"poster_{meta['width'] * scale}x{meta['height'] * scale}.{ext}" if format != "pdf" else "poster.pdf"
    return FileResponse(out, media_type="application/octet-stream", filename=download_name)


@app.get("/api/artifacts/{generation_id}/download")
async def download(generation_id: str, filename: str):
    path = get_artifact_path(generation_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)


@app.get("/api/artifacts/{generation_id}/source")
async def source(generation_id: str):
    path = get_artifact_path(generation_id, "poster.html")
    if path is None:
        raise HTTPException(status_code=404, detail="source not found")
    return FileResponse(path, media_type="text/html", filename=path.name)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
