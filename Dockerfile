FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies if needed (e.g. for cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
CMD ["python", "main.py"]
