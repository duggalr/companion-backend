web: gunicorn app.index:app --workers=4 --worker-class=uvicorn.workers.UvicornWorker
worker: celery -A api.index.celery worker --loglevel=info --concurrency=2