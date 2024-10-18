import os
from dotenv import load_dotenv, find_dotenv
if 'PRODUCTION' not in os.environ:
    ENV_FILE = find_dotenv()
    load_dotenv(ENV_FILE)

from pydantic import BaseModel
from openai import AsyncOpenAI
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import docker
from celery import Celery
from celery.result import AsyncResult


### Create FastAPI instance with custom docs and openapi url
app = FastAPI(
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://www.companionai.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # Log available environment variables
# logging.info("Available Environment Variables:")
# for key in os.environ:
#     logging.info(f"{key}: {os.environ[key]}")

# # Access your specific variable
# redis_url = os.getenv('REDIS_URL')
# if redis_url:
#     logging.info(f"Redis URL: {redis_url}")
# else:
#     logging.error("REDIS_URL is not set.")


import os
import logging

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a file handler
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)

# Create a formatter and set it for the handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

# Log available environment variables
logger.info("Available Environment Variables:")
for key in os.environ:
    logger.info(f"{key}: {os.environ[key]}")

# Access your specific variable
redis_url = os.getenv('REDIS_URL')
if redis_url:
    logger.info(f"Redis URL: {redis_url}")
else:
    logger.error("REDIS_URL is not set.")


# fp = '/opt/elasticbeanstalk/deployment/env'
# li = open(fp).readlines()
# for line in li:
#     k, v = line.split('=')[0], line.split('=')[1]
#     os.environ[k] = v

# for val in os.environ:
#     print(val)

# print(os.environ['REDIS_URL'])

# Initialize Celery
celery = Celery(
    __name__,
    backend = f"redis://default:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_URL']}/0",
    broker = f"redis://default:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_URL']}/0",
)

# if 'PRODUCTION' in os.environ:
#     print(f"CONNECTED")
#     celery = Celery(
#         __name__,
#         backend = f"redis://{os.environ['REDIS_USERNAME']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_URL']}/0",
#         broker = f"redis://{os.environ['REDIS_USERNAME']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_URL']}/0",
#     )
# else:
#     celery = Celery(
#         __name__,
#         backend = "redis://127.0.0.1",
#         broker = "redis://127.0.0.1:6379/0",
#     )

# Initialize Docker client
client = docker.from_env()

print(f"PRODUCTION TEST: {os.environ['PRODUCTION']} | test")


## Celery Tasks ##
@celery.task
def execute_code_in_container(language: str, code: str):
    """
    Task to run user-submitted code inside a Docker container.
    """
    # Set up language-specific Docker image
    docker_image = {
        "python": "python:3.12-slim",
        "nodejs": "node:14-slim"
    }.get(language)

    if not docker_image:
        raise ValueError("Unsupported language")

    # Write the user's code to a temporary file
    host_code_dir = "/tmp"  # Directory on the host
    code_file_name = "submission_code.py"  # Name of the file
    host_code_file = os.path.join(host_code_dir, code_file_name)

    with open(host_code_file, "w") as f:
        f.write(code)

    # The code will be placed in the /app directory inside the container
    container_code_file = f"/app/{code_file_name}"

    # Create the command to run inside the container
    exec_cmd = {
        "python": f"python {container_code_file}",
        "nodejs": f"node {container_code_file}"
    }.get(language)

    # Initialize Docker client
    client = docker.from_env()

    # Run the code inside a Docker container
    container = client.containers.run(
        image=docker_image,
        command=exec_cmd,
        volumes={host_code_dir: {"bind": "/app", "mode": "rw"}},  # Mount the entire /tmp directory
        working_dir="/app",
        detach=True,
        mem_limit="512m",
        cpu_period=100000,
        cpu_quota=50000  # limits CPU to 50% of a single CPU core
    )

    # Wait for the container to complete
    result = container.wait()

    # Capture the container logs (output from the code execution)
    logs = container.logs().decode("utf-8")

    # # Remove the container explicitly
    container.remove()

    if result["StatusCode"] == 0:
        return {"success": True, "output": logs}
    else:
        return {"success": False, "output": logs}


## Util Functions for Views ##
def _prepate_tutor_prompt(user_question, student_code, student_chat_history):
    prompt = """##Instructions:
You will be assisting a student who is learning Python, by being their upbeat, encouraging tutor. 
Your primary goal is to guide and mentor them, helping them learn Python effectively, but also to become a great individual thinker. Please adhere to these guidelines. See examples below of what not to say, and what to say instead.
No Direct Answers: Do not provide direct code solutions to the students' questions or challenges. Instead, focus on providing hints, explanations, and guidance that help them understand and solve the problems on their own. For questions students ask, don't simply provide the answer. Instead, provide a hint and try to ask the student a follow-up question/suggestion. Under no circumstance should you provide the student a direct answer to their problem/question.
Encourage Problem Solving: Always encourage the students to think through the problems themselves. Ask leading questions that guide them toward a solution, and provide feedback on their thought processes.
Make sure you consider both correctness and efficiency. You want to help the student write optimal code, that is also correct for their given problem.
Only ask one question or offer only one suggestion at a time. Wait for the students response before asking a new question or offering a new suggestion.
Encourage the student. Always motivate the student and provide encourage, even when they are struggling or haven't figured out the solution yet. This will help provide motivation and elicit positive emotion for the student. 

##Example Student Question:
# Find the total product of the list

list_one = [2,23,523,1231,32,9]
total_product = 0
for idx in list_one:
    total_product = idx * idx

I'm confused here. I am multiplying idx and setting it to total_product but getting the wrong answer. What is wrong?

##Example Bad Answer (Avoid this type of answer):
You are correct in iterating through the list with the for loop but at the moment, your total_product is incorrectly setup. Try this instead:
list_one = [2,23,523,1231,32,9]
total_product = 1
for idx in list_one:
    total_product = total_product * idx

##Example Good Answer: (this is a good answer because it identifies the mistake the student is making but instead of correcting it for the student, it asks the student a follow-up question as a hint, forcing the student to think on their own)
You are on the right track. Pay close attention to the operation you are performing in the loop. You're currently multiplying the number with itself, but you want to find the product of all numbers. What operation should you use instead to continuously update 'total_product'?

##Previous Chat History:
{student_chat_history}

##Student Question:
{question}

##Student Code:
{student_code}

##Your Answer:
"""

    prompt = prompt.format(
        question=user_question,
        student_code=student_code,
        student_chat_history=student_chat_history
    )
    return prompt
    # prompt = """Generate a short, 100-word funny children story."""
    # return prompt

async def generate_async_response_stream(user_question, user_code, past_user_messages_str):
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_KEY']
    )
    model = "gpt-4o-mini"

    prompt = _prepate_tutor_prompt(
        user_question = user_question,
        student_code = user_code,
        student_chat_history = past_user_messages_str
    )
    response_stream = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        model=model,
        stream=True
    )

    async for chunk in response_stream:
        # print('res:', chunk)
        if chunk.choices[0].finish_reason == 'stop':
            yield None
        else:
            content = chunk.choices[0].delta.content
            if content:
                yield content


## Views ##

class CodeExecutionRequest(BaseModel):
    language: str
    code: str


@app.get("/testing-dev")
async def dev_test_hello_world():
    print("ENV VARS:", os.environ)
    return {'message': 'Hello World!'}


@app.websocket("/ws_handle_chat_response")
async def websocket_handle_chat_response(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:  # Keep receiving messages in a loop
            data = await websocket.receive_json()
            print('Received data:', data)

            user_question = data['text'].strip()
            user_code = data['user_code']
            all_user_messages_str = data['all_user_messages_str']
            print(f"All Messages: {all_user_messages_str}")

            # Respond to the user
            async for text in generate_async_response_stream(
                user_question=user_question,
                user_code=user_code,
                past_user_messages_str=all_user_messages_str
            ):
                if text is None:
                    await websocket.send_text('MODEL_GEN_COMPLETE')
                else:
                    await websocket.send_text(text)

    except WebSocketDisconnect:
        print("WebSocket connection closed")
        await websocket.close()

    # await websocket.accept()
    # try:
    #     data = await websocket.receive_json()
    #     print('Received data:', data)
    #     # await websocket.send_text('hello')
    #     # # {'text': 'test', 'sender': 'user', 'type': 'user_message', 'complete': True}

    #     user_question = data['text'].strip()
    #     user_code = data['user_code']
    #     # all_user_messages_str = '\n'.join(data['all_messages'])
    #     all_user_messages_str = data['all_user_messages_str']
    #     print(f"All Messages: {all_user_messages_str}")

    #     async for text in generate_async_response_stream(
    #         user_question = user_question,
    #         user_code = user_code,
    #         past_user_messages_str = all_user_messages_str
    #     ):
    #         if text is None:
    #             await websocket.send_text('MODEL_GEN_COMPLETE')
    #         else:
    #             await websocket.send_text(text)

    # except WebSocketDisconnect:
    #     print("WebSocket connection closed")
    #     await websocket.close()


@app.post("/execute_user_code")
async def execute_code(request: CodeExecutionRequest):
    """
    Endpoint to submit code for execution.
    """
    user_language = request.language
    user_code = request.code
    print(f"Language: {user_language} | Code: {user_code}")

    task = execute_code_in_container.delay(
        language = user_language,
        code = user_code
    )
    return {"task_id": task.id}
  

@app.get("/task/status/{task_id}")
async def get_status(task_id: str):
    task_result = AsyncResult(task_id)
    return {"task_id": task_id, "status": task_result.status}


@app.get("/result/{task_id}")
def get_result(task_id: str):
    """
    Endpoint to check the result of the execution.
    """
    print(f"Task ID: {task_id}")
    task_result = celery.AsyncResult(task_id)
    result_data = task_result.get()

    print(f"result-data: {result_data}")
    result_output_status = result_data['success']
    result_output_value = result_data['output']
    return {
        "result_output_status": result_output_status,
        "result_output_value": result_output_value
    }
