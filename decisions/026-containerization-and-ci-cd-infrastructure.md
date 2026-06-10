# ADR 026 — Containerization and CI/CD Infrastructure

**Date:** 2026-06-09
**Component:** `Dockerfile`, `.github/workflows/`, `docker-compose.yml`
**Status:** Decided

---

## Context

The project needs to run in two environments: a local Windows development machine
(Python 3.14) and a containerized Linux deployment (Python 3.11). The API must
start reliably in both, the CI pipeline must run on every push without depending
on files that are gitignored, and the Docker build must be cache-efficient.

Several of these decisions are mechanical — standard Docker/CI practice — but
they interact with project-specific constraints (the gitignored model artifact,
the slow integration tests, the Python version mismatch) in ways worth
recording.

---

## Decision

### 1. Base image: `python:3.11-slim`

The Docker image uses `python:3.11-slim`, not `python:3.14` (the development
version). `slim` omits build toolchains and documentation, reducing image size
without removing anything the API needs at runtime. Python 3.11 is the latest
stable release with wide package support; 3.14 is a pre-release used for
development but not yet appropriate for a deployment image.

### 2. Artifacts copied into the image

The model artifact (`artifacts/model/`) and baseline (`data/baseline/`) are
copied into the Docker image at build time with `COPY`. They are not fetched
from cloud storage at container startup.

This is a v1 deployment decision. A production system would pull artifacts from
S3/GCS at startup so the image and the model can be versioned independently. For
v1, copying into the image keeps the deployment self-contained — the container
carries everything it needs — and avoids introducing a cloud storage dependency
before there is a concrete reason to manage artifacts separately.

### 3. Layer ordering for cache efficiency

`requirements.txt` is copied and `pip install` runs before the source code is
copied. Docker caches each `COPY`/`RUN` layer; if dependencies change less often
than source code (which they do), this ordering means `pip install` is reused
from cache on most builds, substantially speeding up local iteration.

### 4. `--host 0.0.0.0` in the uvicorn command

The Dockerfile's `CMD` runs uvicorn with `--host 0.0.0.0`. The default
`127.0.0.1` binds only to the container's loopback interface, which is
unreachable from the host. `0.0.0.0` binds to all interfaces inside the
container, making the API reachable via Docker's port mapping.

### 5. CI triggers: push and pull request to main

The GitHub Actions workflow triggers on `push` and `pull_request` to the `main`
branch. This is standard CI practice — every proposed change is tested before
merge, and the merged result is tested again.

### 6. CI Python version: 3.11

CI runs on Python 3.11, matching the Docker image, not the development
environment's 3.14. The CI environment is the deployment environment's proxy;
testing on the same Python version the container will use catches
version-specific bugs before they reach the image.

### 7. Slow tests excluded from CI

The CI workflow runs `pytest --ignore=tests/test_scripts`. The two integration
tests in `tests/test_scripts/` (training and monitoring orchestration) tune real
models and take several minutes. They are valuable for local verification but
too slow for a CI feedback loop that should complete in under a minute. They
remain runnable locally with `pytest -m slow`.

### 8. API tests use mocked model and baseline

The model artifact and baseline are gitignored — they do not exist on a fresh
clone. The API tests (`tests/test_api/`) therefore cannot load the real model
from disk. Instead, they construct a minimal `ModelArtifact` and baseline
dict in the test file's module-scoped fixture, and override the FastAPI
`app.state` before each test. This keeps the API tests fast, isolated, and
runnable in CI without requiring a prior training run.

### 9. `docker-compose.yml` left empty

The project has a single service (the API). A `docker-compose.yml` file exists
as a placeholder but defines no services. Docker Compose adds value when
multiple services need to be orchestrated together (API + database + worker).
For v1's single-container deployment, `docker build` and `docker run` are
sufficient; adding Compose would be ceremony with no benefit. The file remains
as a scaffold for v2 if additional services are added.

---

## Consequences

**For local development:** The Docker image builds and runs identically on
Windows and Linux. A developer can test the containerized API locally with
`docker build -t ml-pipeline . && docker run -p 8000:8000 ml-pipeline`.

**For CI:** Every push to `main` (or a PR targeting `main`) triggers a fast test
suite that verifies the data, model, monitoring, and API layers without
requiring real artifacts or long-running integration tests.

**For deployment:** The Docker image is self-contained — it carries the model
and baseline inside it. Deploying to Cloud Run or any container platform
requires only the image, with no external artifact fetch at startup.