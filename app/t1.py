import os
import docker


# Set up language-specific Docker image
# docker_image = {
#     "python": "python:3.12-slim",
# }

docker_image = "python:3.12-slim"
val = f"python `print('hello')`"

# Initialize Docker client
client = docker.from_env()

# Run the code inside a Docker container
container = client.containers.run(
    image=docker_image,
    command=val,
    working_dir="/app",
    detach=True,
    mem_limit="512m",
    cpu_period=100000,
    cpu_quota=50000  # limits CPU to 50% of a single CPU core
)
