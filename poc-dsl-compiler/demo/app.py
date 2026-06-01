"""
app.py — FastAPI application for the Zigflow DSL Compiler Demo.

Routes:
    GET  /            → index.html (Jinja2)
    GET  /api/levels  → list of {level, description} for all 14 difficulty levels
    POST /api/pipeline → run full pipeline for a generated workflow level
    POST /api/compile  → compile a user-supplied workflow JSON (Paste JSON mode)

All compiler calls are dispatched via asyncio.run_in_executor so synchronous
compiler functions never block the async event loop.
"""

import asyncio
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from demo.pipeline import (
    DESCRIPTIONS,
    compile_custom,
    run_full_pipeline,
)

# ─── app setup ────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Zigflow DSL Compiler Demo", version="1.0.0")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ─── request/response models ──────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    level: int = Field(..., ge=1, le=14, description="Difficulty level 1–14")


class CompileRequest(BaseModel):
    workflow: dict = Field(..., description="Raw workflow JSON {nodes, edges}")


# ─── routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/levels")
async def get_levels():
    """Return all 14 difficulty levels with descriptions."""
    return [
        {"level": level, "description": desc}
        for level, desc in DESCRIPTIONS.items()
    ]


@app.post("/api/pipeline")
async def pipeline(req: PipelineRequest):
    """Generate a workflow for the given level and run the full compiler pipeline."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, partial(run_full_pipeline, req.level))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(content=result)


@app.post("/api/compile")
async def compile_endpoint(req: CompileRequest):
    """Compile a user-supplied workflow JSON (Paste JSON mode)."""
    if "nodes" not in req.workflow or "edges" not in req.workflow:
        raise HTTPException(
            status_code=422,
            detail="Workflow JSON must have 'nodes' and 'edges' keys.",
        )
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, partial(compile_custom, req.workflow))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(content=result)
