FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libasound2 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    chromium \
    chromium-driver \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variable to avoid Chrome sandbox issues
ENV CHROME_BIN=/usr/bin/chromium

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Run your script
CMD ["python", "main.py"]
