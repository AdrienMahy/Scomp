FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including postgresql client)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code - preserve the backend folder structure
# This ensures src/ is at the correct path for project_root calculation
COPY . backend/

# Expose port 8001
EXPOSE 8001

# Run from the backend directory
WORKDIR /app/backend

# Use entrypoint to run migrations and start API
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["python3 -m alembic upgrade heads && uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload"]

