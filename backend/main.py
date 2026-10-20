import traceback
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .models.schemas import GenerateRequest, RecompileRequest
from .orchestrator import Orchestrator, OrchestratorError
from .services.artifact_service import get_artifact_path
from pathlib import Path
from .config import settings


app = FastAPI(title="AI Marketing Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orch = Orchestrator()


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    try:
        res = await orch.generate(req.prompt, width=req.width, height=req.height, brand=req.brand)
        preview = f"/api/artifacts/{res['generation_id']}/preview"
        return JSONResponse({"generation_id": res["generation_id"], "analysis": res["analysis"], "creative": res["creative"], "html": res["html"], "preview_url": preview})
    except OrchestratorError as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recompile")
async def recompile(req: RecompileRequest):
    gen_dir = Path(settings.OUTPUT_DIR) / req.generation_id
    if not gen_dir.exists():
        raise HTTPException(status_code=404, detail="generation id not found")

    edited_file = gen_dir / "poster_edited.html"
    edited_file.write_text(req.html, encoding="utf-8")

    try:
        from .scripts.render_poster import render_html_to_png_async

        out = gen_dir / f"poster_edited.{req.format or 'png'}"
        width = 1080
        height = 1350
        await render_html_to_png_async(req.html, out, width, height, format=req.format or "png")
        return {"generation_id": req.generation_id, "preview_url": f"/api/artifacts/{req.generation_id}/preview"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/artifacts/{generation_id}/preview")
async def preview(generation_id: str):
    path = get_artifact_path(generation_id, "poster.png")
    if path is None:
        raise HTTPException(status_code=404, detail="preview not found")
    return FileResponse(path)


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
