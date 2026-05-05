# ── Builder ──
FROM python:3.12-slim AS builder
WORKDIR /app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/src/ src/
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir uvicorn

# ── Runtime ──
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/dramatiq /usr/local/bin/dramatiq

COPY backend/src/ src/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini .

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    poppler-utils \
    tesseract-ocr \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "breaking_law.main:app", "--host", "0.0.0.0", "--port", "8000"]
