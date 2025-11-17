# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose FastAPI port
EXPOSE 8000

# Set environment variables (optional, for production best practice)
ENV PYTHONUNBUFFERED=1

# Use the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
