FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
COPY labomatics ./labomatics
RUN poetry install --only main --no-directory
CMD ["poetry", "run", "api"]
