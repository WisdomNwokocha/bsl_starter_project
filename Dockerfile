# Builds a container that serves the BSL web app (src/web_server.py) for
# cloud hosting (Railway, Fly.io, Render, etc). Not used for local dev —
# keep using your venv + requirements.txt for that.

FROM python:3.12-slim

# mediapipe/opencv still need a couple of native libs even in headless mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Only what's needed to SERVE the app — training data/raw_videos/venv are
# excluded via .dockerignore, keeping the image small and the build fast.
COPY src ./src
COPY web_ui ./web_ui
COPY models ./models

# Railway/Fly/Render set $PORT at runtime; default to 8000 for local
# `docker run` testing.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.web_server:app --host 0.0.0.0 --port ${PORT}"]
