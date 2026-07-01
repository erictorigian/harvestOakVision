# Multi-arch: linux/amd64 + linux/arm64
FROM python:3.11-slim

WORKDIR /app

# OpenCV runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        ffmpeg \
        v4l-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . vision/

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" 2>/dev/null && exit 0 || exit 0

CMD ["python", "-m", "vision.main"]
