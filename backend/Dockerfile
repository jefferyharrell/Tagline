# syntax=docker/dockerfile:1.4
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libjpeg-dev libheif-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
RUN pip install uv

# Set workdir
WORKDIR /app

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Copy the Alembic migration files
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

# Copy the rest of the application
COPY app/ ./app/

# Install Python dependencies using uv at system level
RUN uv pip install --system -r pyproject.toml

# Expose the PORT env variable
EXPOSE ${PORT:-8000}

# Start the application - run migrations first, then start the server
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host '' --port ${PORT:-8000}"]
