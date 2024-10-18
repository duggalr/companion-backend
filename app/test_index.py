import time
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import patch
from celery.result import AsyncResult

from app.index import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_dev_test_hello_world():
    """Test GET /testing-dev endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/testing-dev")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World!"}


@pytest.mark.asyncio
async def test_websocket_handle_chat_response():
    """Test WebSocket connection and message handling."""
    with client.websocket_connect("/ws_handle_chat_response") as websocket:
        websocket.send_json({"input": "test"})
        response = websocket.receive_text()
        while response != "MODEL_GEN_COMPLETE":
            assert isinstance(response, str)
            response = websocket.receive_text()
        websocket.close()


# @pytest.mark.asyncio
# @patch("index.execute_code_in_container.delay")  # Mock the Celery task
# async def test_execute_code(mock_execute_code):
#     """Test POST /execute_user_code endpoint with Celery mock."""
#     mock_execute_code.return_value.id = "test-task-id"

#     request_data = {
#         "language": "python",
#         "code": "print('Hello, World!')"
#     }

#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.post("/execute_user_code", json=request_data)

#     assert response.status_code == 200
#     assert response.json() == {"task_id": "test-task-id"}
#     mock_execute_code.assert_called_once_with(
#         language="python",
#         code="print('Hello, World!')"
#     )


# @pytest.mark.asyncio
# @patch("index.AsyncResult")
# async def test_get_status(mock_async_result):
#     """Test GET /task/status/{task_id} endpoint."""
#     mock_async_result.return_value.status = "SUCCESS"

#     task_id = "test-task-id"
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/task/status/{task_id}")

#     assert response.status_code == 200
#     assert response.json() == {"task_id": task_id, "status": "SUCCESS"}
#     mock_async_result.assert_called_once_with(task_id)


# @pytest.mark.asyncio
# @patch("index.AsyncResult")
# async def test_get_result(mock_async_result):
#     """Test GET /result/{task_id} endpoint."""
#     task_result_mock = {
#         'success': True,
#         'output': 'Execution completed successfully!'
#     }
#     mock_async_result.return_value.get.return_value = task_result_mock

#     task_id = "test-task-id"
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.get(f"/result/{task_id}")

#     assert response.status_code == 200
#     assert response.json() == {
#         "result_output_status": True,
#         "result_output_value": "Execution completed successfully!"
#     }
#     mock_async_result.assert_called_once_with(task_id)


# @pytest.mark.asyncio
# async def test_execute_code_integration():
#     request_data = {
#         "language": "python",
#         "code": "print('Hello, World!')"
#     }

#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.post("/execute_user_code", json=request_data)

#     task_id = response.json()["task_id"]
#     print(f"Waiting for 10 seconds for task to complete...")
#     time.sleep(10)

#     # Get status of the task
#     task_result = AsyncResult(task_id)
#     print(f"Task Result: {task_result}")
#     assert task_result.status == "SUCCESS"

#     # Get the result of the task
#     result_data = task_result.get()
#     print(f"Result Data: {result_data}")
#     assert result_data["success"]
#     assert result_data["output"] == "Hello, World!\n"
