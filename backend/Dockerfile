FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock alembic.ini ./
COPY labomatics ./labomatics
COPY alembic ./alembic
RUN poetry install --only main --no-directory
CMD ["poetry", "run", "api"]
