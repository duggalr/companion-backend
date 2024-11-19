# Base Python image
FROM python:alpine

# Set the working directory
WORKDIR /app

# System Dependencies and Poetry
RUN pip install poetry
COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

# Copy the rest of the application code
COPY . /app

# ENTRYPOINT ["poetry", "run"]

# # # Install system dependencies and Poetry
# # RUN apt-get update && apt-get install -y curl && \
# #     curl -sSL https://install.python-poetry.org | python3 - && \
# #     apt-get clean

# # Add Poetry to PATH
# ENV PATH="/root/.local/bin:$PATH"

# # Copy the project files for Poetry dependencies
# COPY pyproject.toml poetry.lock /app/

# # Install dependencies
# RUN poetry install --no-root

# # Copy the rest of the application code
# COPY . /app

# # Set the default entrypoint
# ENTRYPOINT ["poetry", "run"]

# FROM python:3.13 AS builder

# ENV PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1
# WORKDIR /app

# RUN pip install poetry
# RUN poetry config virtualenvs.in-project true

# COPY pyproject.toml poetry.lock ./
# RUN poetry install --no-root



# # FROM python:slim
# # WORKDIR /app
# # COPY --from=builder /app/.venv .venv/
# # COPY . .
# # CMD ["/app/.venv/bin/fastapi", "run"]

# # TODO: install poetry via dockerfile