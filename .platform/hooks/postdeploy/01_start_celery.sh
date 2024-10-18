# This script starts the Celery service after deployment

# Start the Celery service
sudo systemctl start celery

# Optionally, check the status to make sure it's running
sudo systemctl status celery