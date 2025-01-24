FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    requests \
    beautifulsoup4 \

# Set a working directory
WORKDIR /app

CMD ["python3"]