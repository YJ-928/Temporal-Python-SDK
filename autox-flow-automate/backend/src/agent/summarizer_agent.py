"""
Summarizer Agent Service

A self-contained FastAPI application that mocks text summarization.

Port: 11003
Endpoint: POST /execute

Example Request:
    POST http://localhost:11003/execute
    {"text": "This is a long article about machine learning..."}

Example Response:
    {"summary": "Article discusses machine learning concepts."}
"""
import uvicorn
from fastapi import Body, FastAPI
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title="Summarizer Agent Service",
    description="Mock text summarization service",
    version="1.0.0"
)


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"text": "Long text content to summarize..."}})

    text: Optional[str] = Field(None, description="Text content to summarize (optional)")


class SummarizeResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"summary": "Brief summary of the content."}})

    success: bool = Field(..., description="Whether the summarization was successful")
    summary: Optional[str] = Field(None, description="Generated summary")
    word_count: Optional[int] = Field(None, description="Word count of original text")


@app.get("/")
async def root():
    return {"service": "Summarizer Agent", "status": "running", "port": 11003, "endpoint": "/execute"}


@app.post("/execute")
async def execute(request: Annotated[Optional[SummarizeRequest], Body()] = None) -> SummarizeResponse:
    text = (request.text if request and request.text else "").strip()
    if not text:
        # No text provided — return a default no-op summary
        return SummarizeResponse(success=True, summary="No content to summarize.", word_count=0)

    words = text.split()
    word_count = len(words)

    # Mock summary: take first sentence or first 20 words
    sentences = text.split(".")
    first_sentence = sentences[0].strip() if sentences else text
    summary = (first_sentence[:100] + "...") if len(first_sentence) > 100 else first_sentence

    logger.info(f"Summarized text: {word_count} words → {len(summary)} char summary")
    return SummarizeResponse(success=True, summary=summary, word_count=word_count)


if __name__ == "__main__":
    logger.info("Starting Summarizer Agent Service on port 11003...")
    uvicorn.run(app, host="0.0.0.0", port=11003, log_level="info")  # noqa: S104
