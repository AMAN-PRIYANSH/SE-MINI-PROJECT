# Web Server image (Phase 3): Flask app + static client on port 5000.
# Build with docker compose (see docker-compose.yml at the repo root).
FROM python:3.12-slim
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY shared ./shared
COPY server ./server
COPY client ./client
COPY training/best_model.json ./training/best_model.json
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
CMD ["python", "-m", "server.app"]
