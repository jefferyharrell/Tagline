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

# Install Python dependencies using uv
RUN uv sync

# Expose the PORT env variable
EXPOSE ${PORT:-8000}

# Start the application - bind to :: and use the PORT environment variable
CMD ["sh", "-c", "uv run uvicorn app.main:app --host '' --port ${PORT:-8000}"]
