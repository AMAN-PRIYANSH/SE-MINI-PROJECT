# DL microservice image (Phase 3): sklearn MLP + PyTorch DNN on port 5002.
# Build with docker compose (see docker-compose.yml at the repo root).
FROM python:3.12-slim
WORKDIR /app
COPY requirements-runtime.txt requirements-torch.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt -r requirements-torch.txt
COPY shared ./shared
COPY services/__init__.py ./services/__init__.py
COPY services/common ./services/common
COPY services/dl ./services/dl
ENV PYTHONUNBUFFERED=1
EXPOSE 5002
CMD ["python", "-m", "services.dl.server"]
