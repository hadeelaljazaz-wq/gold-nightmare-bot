FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Set environment variable for Flask
ENV PORT=8080

# Expose port
EXPOSE $PORT

# Run the bot
CMD ["python", "main.py"]
