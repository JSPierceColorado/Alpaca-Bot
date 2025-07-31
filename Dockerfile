# Use official Python base image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for pip packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file into the image
COPY requirements.txt .

# Upgrade pip to latest
RUN pip install --upgrade pip

# 🛠️ Fix for alpaca-trade-api dependency issue
RUN pip install websockets==10.4

# Install remaining Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of your app's code into the container
COPY . .

# Run the application
CMD ["python", "main.py"]
