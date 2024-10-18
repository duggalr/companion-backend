#!/bin/bash

# Start Celery worker
celery -A app.index.celery worker --loglevel=info --concurrency=2 &