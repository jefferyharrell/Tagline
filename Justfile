# Justfile for Tagline Backend
# Your one-stop CLI for all the commands you never want to memorize again.
# Usage: just <recipe>

# Show all available commands
default:
    just help

# Set up dev environment
setup:
    #!/usr/bin/env bash
    if [ ! -d "venv" ]; then python3source -m venv venv; fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements-dev.txt
    if [ ! -f ".env" ]; then cp .env.example .env; fi
    echo -e "\033[1;32mSetup complete! Activate your venv with 'source venv/bin/activate' and start coding.\033[0m"

format:
    source venv/bin/activate && isort .
    source venv/bin/activate && black .

lint:
    source venv/bin/activate && ruff check --fix .
    source venv/bin/activate && pyright --project .

# Testing
unit-tests:
    source venv/bin/activate && PYTHONPATH=. pytest -s -v tests/unit -m unit -rs

e2e-tests:
    source venv/bin/activate && pytest -s -v tests/e2e -m e2e -rs

test:
    just unit-tests
    just e2e-tests

coverage:
    source venv/bin/activate && pytest tests/unit -m unit --cov=app --cov-report=term-missing

all:
    just format
    just lint
    just test
    just pre-commit

run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

# Remove Python cache files, test artifacts, and __pycache__ dirs
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    rm -rf .pytest_cache .mypy_cache .coverage coverage.xml
    echo "Cleaned up Python and test artifacts."

# Stop everything, rebuild images, and start fresh
rebuild:
    just down
    docker compose build --no-cache
    just up
    echo "Rebuilt and started fresh containers."

# Upgrade all pip packages in requirements-dev.txt
update-deps:
    source venv/bin/activate
    pip install --upgrade -r requirements-dev.txt
    pip list --outdated
    echo "Dependencies updated. Check above for anything still out-of-date."

# Pre-Commit
pre-commit:
    # Run the pre-commit hoook
    source venv/bin/activate && pre-commit run --all-files

# Docker Compose
up:
    # Start all containers in the background
    docker compose up -d

down:
    # Stop all containers
    docker compose down

build:
    # Build Docker images
    docker compose build

pip-install:
    # Install/sync Python dependencies inside the backend container
    docker compose exec backend pip install -r /code/requirements.txt

logs:
    # Tail backend logs
    docker compose logs -f

shell:
    # Open a bash shell in the backend container
    docker exec -it tagline-backend-dev /bin/bash

# Alembic migrations (inside Docker)
migrate:
    # Apply all migrations in the backend container
    docker exec -it tagline-backend-dev alembic upgrade head

makemigration MESSAGE="Describe your migration":
    # Create a new Alembic migration (autogenerate) in Docker
    docker exec -it tagline-backend-dev alembic revision --autogenerate -m "{{MESSAGE}}"

dbshell:
    # Open a Postgres shell in the Postgres container for integration/dev DB
    docker exec -it tagline-postgres-dev psql -U tagline -d tagline

# Connect to the Redis shell in the dev container
redis-shell:
	docker exec -it tagline-redis-dev redis-cli

# Clean up
prune:
    # Remove stopped containers, unused networks, dangling images/volumes
    docker system prune -f

# Show help
help:
    @echo "\nJustfile: Tagline Backend Project Helper\n"
    @just --list
    @echo "\nRun 'just <command>' to execute a task."
    @echo "For details: see docs/alembic-workflow.md and README.md."
