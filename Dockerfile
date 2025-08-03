FROM python:3.12-slim

# Install system dependencies (none needed for this version, but keep minimal for Google Sheets + networking)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set Python environment variables for best practice
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command
CMD ["python", "main.py"]
