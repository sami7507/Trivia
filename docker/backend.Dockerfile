# Triavia API — the model is trained at build time so the image is self-contained.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend backend
COPY database database
COPY model model
RUN mkdir -p assets data/raw data/processed && python model/train.py && \
    useradd --create-home --uid 10001 app && \
    mkdir -p /app/database/data && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request as u; u.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/api/v1/health', timeout=4)"
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
