# syntax=docker/dockerfile:1.4
FROM python:3.13-slim AS base

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

# Copy the rest of the application
COPY app/ ./app/

# Install dependencies with uv
RUN uv pip install --system app

# Expose port
EXPOSE 8000

# Start the application with auto-reload for development
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
