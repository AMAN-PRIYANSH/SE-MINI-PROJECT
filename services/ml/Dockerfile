# ML microservice image (Phase 3): Logistic Regression + Random Forest on port 5001.
# Build with docker compose (see docker-compose.yml at the repo root).
FROM python:3.12-slim
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY shared ./shared
COPY services/__init__.py ./services/__init__.py
COPY services/common ./services/common
COPY services/ml ./services/ml
ENV PYTHONUNBUFFERED=1
EXPOSE 5001
CMD ["python", "-m", "services.ml.server"]
