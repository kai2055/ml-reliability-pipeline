
"""FastAPI dependencies for injecting shared resources into routes."""

from fastapi import Request
from src.models.registry import ModelArtifact



def get_model(request: Request) -> ModelArtifact:
    """Return the model loaded at startup"""
    return request.app.state.model


def get_baseline(request: Request) -> dict:
    """Return the baseline loaded at startup"""
    return request.app.state.baseline

