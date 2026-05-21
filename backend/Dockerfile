# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies (needed for PyMuPDF / building wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directories for uploads and DB
RUN mkdir -p uploads chroma_db

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Railway's PORT environment variable
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
