FROM python:3.12-slim

WORKDIR /app

# System dependencies for compiling some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install known dependency first to avoid pip resolution conflict
RUN pip install msgpack==1.0.8

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Default command
CMD ["python", "main.py"]
