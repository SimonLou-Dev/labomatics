#!/bin/bash
set -e

echo "Exécution des migrations Alembic..."
cd /app
poetry run alembic upgrade head

echo "Migrations terminées!"
