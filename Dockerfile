# Use an official Python base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system build dependencies (needed for compiling some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements file first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and ensure wheel is available to avoid source build issues
RUN pip install --upgrade pip wheel

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy project files into the container
COPY . .

# Set default command
CMD ["python", "main.py"]
