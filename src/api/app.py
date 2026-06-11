"""FastAPI application factory and lifespan management."""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request

from src.models.registry import load_model
from src.monitoring.baseline_loader import load_baseline
from src.api.routes import router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
access_log = logging.getLogger("access")

MODEL_DIR = Path("artifacts/model")
BASELINE_DIR = Path("data/baseline")


def _ensure_artifacts() -> None:
    """Download model + baseline from GCS unless present locally."""
    bucket_name = os.getenv("ARTIFACT_BUCKET")
    if bucket_name is None:
        return  # local dev: use files on disk

    # Lazy import – only needed in production (Cloud Run)
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    targets: dict[str, Path] = {
        os.getenv("MODEL_PREFIX", "model/v1"): Path("artifacts/model"),
        os.getenv("BASELINE_PREFIX", "baseline/v1"): Path("data/baseline"),
    }

    for prefix, dest in targets.items():
        dest.mkdir(parents=True, exist_ok=True)
        for blob in bucket.list_blobs(prefix=prefix):
            local_file = dest / Path(blob.name).relative_to(prefix)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_file))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load shared resources at startup, release at shutdown."""
    _ensure_artifacts()
    app.state.model = load_model(MODEL_DIR)
    app.state.baseline = load_baseline(BASELINE_DIR)
    yield


app = FastAPI(
    title="Spreekredit ML Reliability API",
    description="Drift detection and credit risk scoring for Spreekredit.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request logging middleware ─────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    access_log.info(
        '{"path": "%s", "method": "%s", "status": %d, "duration_ms": %.1f}',
        request.url.path,
        request.method,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(router)
