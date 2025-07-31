FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip

# Preinstall msgpack to avoid missing version in Alpaca
RUN pip install msgpack==1.0.8

# Install all project dependencies
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
