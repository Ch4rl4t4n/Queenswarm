FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini .
COPY backend/.coveragerc .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/tests ./tests
COPY backend/plugins ./plugins
COPY docs/harness ./docs/harness

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade heads && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
