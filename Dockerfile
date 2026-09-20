# ── Stage 1: build deps ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ───────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend_server.py .
COPY core/ ./core/
COPY infrastructure/watchlist.json ./infrastructure/watchlist.json

# Create empty data files so the server doesn't fail on first boot.
# On Railway you can mount a persistent volume at /app/data and point
# HISTORY_FILE / USERS_FILE env vars there for durable storage.
RUN echo "[]" > local_history.json && \
    echo "[]" > local_users.json

# Cloud hosts inject PORT; default to 8000 for local docker run
ENV PORT=8000

EXPOSE $PORT

# Healthcheck — Railway and Render use this to verify the container is up
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')"

CMD ["sh", "-c", "python backend_server.py"]
