#!/bin/bash

# Install Docker on Amazon Linux 2023 (for remote code execution)
sudo yum update -y
sudo amazon-linux-extras enable docker
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Optional: enable Docker to start on boot
sudo systemctl enable docker