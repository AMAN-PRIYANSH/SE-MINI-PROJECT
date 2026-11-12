# QML microservice image (Phase 3): VQC + quantum-kernel SVM on port 5003.
# Build with docker compose (see docker-compose.yml at the repo root).
FROM python:3.12-slim
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt pennylane==0.45.1
COPY shared ./shared
COPY services/__init__.py ./services/__init__.py
COPY services/common ./services/common
COPY services/qml ./services/qml
ENV PYTHONUNBUFFERED=1
EXPOSE 5003
CMD ["python", "-m", "services.qml.server"]
