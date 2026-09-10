FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry
COPY pyproject.toml poetry.lock alembic.ini ./
COPY labomatics ./labomatics
COPY alembic ./alembic
RUN poetry install --only main --no-directory
CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run api"]
