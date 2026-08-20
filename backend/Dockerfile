FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --timeout=1000 -r requirements.txt

# Copy application code
COPY . .

# Create entrypoint script
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]