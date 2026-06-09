
""" FastAPI application factory and lifespan management. """

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.models.registry import load_model
from src.monitoring.baseline_loader import load_baseline

from src.api.routes import router



MODEL_DIR = Path("artifacts/model")
BASELINE_DIR = Path("data/baseline")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load shared resources at startup, release at shutdown"""
    app.state.model = load_model(MODEL_DIR)
    app.state.baseline = load_baseline(BASELINE_DIR)
    yield



app = FastAPI(
    title="Datatroniq ML Reliability API",
    description="Drift detection and credit risk scoring for Datatroniq.",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(router)
