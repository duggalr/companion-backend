# Use the slim Python image
FROM python:slim

# Set environment variables to prevent Python from writing .pyc files and to run in non-interactive mode
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies needed for Poetry and Python
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy the project files
COPY pyproject.toml poetry.lock ./
COPY . /app

# Install project dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Expose the app's port (replace 8000 with your app's actual port)
EXPOSE 8000

# Set the command to run your FastAPI app (replace 'app.main:app' with your actual module and app name)
CMD ["poetry", "run", "uvicorn", "app.index:app", "--host", "0.0.0.0", "--port", "8000"]