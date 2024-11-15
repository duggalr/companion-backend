# from your_project.tasks import execute_code_in_container
from app.index import execute_code_in_container

# Enqueue the task
async_result = execute_code_in_container.delay("python", "print('Hello, Celery!')")

# Check the task's result
print(async_result.get(timeout=20))  # Wait for up to 20 seconds

