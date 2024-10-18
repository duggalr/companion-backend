# This script will create the systemd service for Celery

cat <<EOF | sudo tee /etc/systemd/system/celery.service
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/var/app/current
ExecStart=/opt/python/run/venv/bin/celery -A app.index.celery worker --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service so it starts on boot
sudo systemctl enable celery