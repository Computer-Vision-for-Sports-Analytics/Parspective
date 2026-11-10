"""FastAPI application entry point.

Phase 1 only exposes ``/health``. The analysis, results and email routes come in Phase 4.
Run locally with: ``uvicorn app.main:app --reload`` from the ``server/`` directory.
"""

from fastapi import FastAPI

from parspective import SCHEMA_VERSION, __version__

app = FastAPI(title="Parspective Mobile API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "analysis_version": __version__, "schema_version": SCHEMA_VERSION}
