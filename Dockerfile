# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run test && npm run build


FROM python:3.12-slim AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PROCTORVISION_ENVIRONMENT=production \
    PROCTORVISION_SERVE_FRONTEND=true \
    PROCTORVISION_PRELOAD_MODEL=true \
    PROCTORVISION_PREFER_OPENVINO=true \
    PROCTORVISION_DATABASE_PATH=/app/storage/data/proctorvision.db \
    PROCTORVISION_EVIDENCE_DIRECTORY=/app/storage/evidence

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-lock.txt ./
COPY backend/requirements-openvino.txt ./backend/requirements-openvino.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-lock.txt \
    && python -m pip install -r backend/requirements-openvino.txt

COPY backend/ ./backend/
RUN python -c "from ultralytics import YOLO; YOLO('yolo11s.pt')"
RUN python backend/scripts/prepare_openvino.py

COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

RUN useradd --create-home --uid 10001 proctorvision \
    && mkdir -p /app/storage/data /app/storage/evidence \
    && chown -R proctorvision:proctorvision /app/storage

USER proctorvision
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
