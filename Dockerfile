FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY requirements-runtime.txt .
RUN pip install --no-cache-dir --timeout=300 -r requirements-runtime.txt

# Copy source code
COPY src/ ./src/

# Create the non‑root user
RUN useradd --create-home appuser

# Create writable artifact directories and give ownership to the user
RUN mkdir -p artifacts/model data/baseline && chown -R appuser:appuser /app

# Switch to the non‑root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\",8000)}/health')"

CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]