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
    allow_origins=["http://localhost:3000", "https://staging.companionai.dev", "https://www.companionai.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize Celery
if 'LOCAL' in os.environ:
    celery = Celery(
        __name__,
        backend = "redis://127.0.0.1",
        broker = "redis://127.0.0.1:6379/0",
    )
else:
    celery = Celery(
        __name__,
        backend = f"{os.environ['REDIS_URL']}/0",
        broker = f"{os.environ['REDIS_URL']}/0",
        # backend = f"redis://default:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_URL']}/0",
        # broker = f"redis://default:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_URL']}/0",
    )


## Celery Tasks ##
@celery.task
def execute_code_in_container(language: str, code: str):
    """
    Task to run user-submitted code inside a Docker container.
    """
    # Set up language-specific Docker image
    docker_image = {
        "python": "python:3.12-slim",
        # "nodejs": "node:14-slim"
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

    MAX_EXECUTION_TIME_IN_SECONDS = 10

    # Initialize Docker client
    client = docker.from_env()

    # Command to run inside the container
    exec_cmd = {
        "python": f"python {container_code_file}",
        "nodejs": f"node {container_code_file}"
    }.get(language)

    result = None
    try:
        container = client.containers.run(
            image = docker_image,
            command = exec_cmd,
            volumes = {host_code_dir: {"bind": "/app", "mode": "rw"}}, # Mount directory
            working_dir = "/app",
            detach = True,
            user = "nobody",
            read_only = True,
            network_mode = "none",
            mem_limit = "512m",
            cpu_period = 100000,
            cpu_quota = 50000,
            pids_limit = 64,
            security_opt = ["no-new-privileges"]
        )
        result = container.wait(
            timeout = MAX_EXECUTION_TIME_IN_SECONDS
        )
        logs = container.logs().decode("utf-8")
    except docker.errors.ContainerError as e:
        logs = f"Error: {str(e)}"
    except docker.errors.APIError as e:
        logs = f"Docker API Error: {str(e)}"
    except docker.errors.DockerException as e:
        logs = f"Docker Execution Error: {str(e)}"
    except Exception as e:
        logs = f"Unexpected Error: {str(e)}"
    finally:
        # Clean up the container
        container.remove(force=True)

    if result is not None:
        if result["StatusCode"] == 0:
            return {"success": True, "output": logs}
        else:
            return {"success": False, "output": logs}
    else:
        return {"success": False, "output": logs}


## Util Functions for Views ##
def _prepate_tutor_prompt(user_question, student_code, student_chat_history):
    # - For example, if the student asks about a specific data structure or algorithm, try to understand their understanding of the underlying concepts like arrays, linked lists, stacks, queues, trees, graphs, and recursion.
    prompt = """##Task:
You will be assisting a student, who will be asking questions on a specific Python Programming Problem.
Your will be their upbeat, encouraging tutor.
- Even though you are encouraging and upbeat, maintain a natural conversation flow. Don't overcompliment in each message. Keep it natural like a good tutor.
Your primary goal is to guide and mentor them, helping them solve their problem effectively, but also to become a great individual thinker. Please adhere to these guidelines. Further instructions are provided below. Also, an example is provided below.
- Please don't guide the student to using any libraries that need pip install as the remote code execution environment doesn't support those libraries.
    - Native python libraries (ie. like math) are completely fine and are supported.

##Instructions:
- Ask or Gauge their pre-requisite knolwedge:
    - Try to understand or gauge the student's understanding of the concept or problem they have asked, before jumping in and providing them with further information or hints.
    - By understanding the student's current understanding of the concept or problem, it will make it easier for you to determine which level of abstraction you should start with, when generating your answer.
- No Over Information:
    - Do not provide over information, for a student's question.
    - Instead, focus on trying to create a conversation with the student.
    - Do not provide the student with the answer in any way. Instead, focus on providing valuable but concise explanations, hints, and follow-up questions, forcing the student to think of the answer on their own.
- No Direct Answers:
    - Do not provide any direct code solutions to the students questions or challenges.
    - Instead, focus on providing high-quality hints, with very concrete examples or detailed explanations.
    - Your goal as a tutor is to provide concrete and detailed guidance to help the student solve the problem on their own.
    - Thus, for questions students ask, don't simply provide the answer. Instead, provide a hint and try to ask the student a follow-up question/suggestion. Under no circumstance should you provide the student a direct answer to their problem/question.
- Encourage Problem Solving:
    - Always encourage the students to think through the problems themselves. Ask leading questions that guide them toward a solution, and provide feedback on their thought processes.
    - Make sure you consider both correctness and efficiency. You want to help the student write optimal code, that is also correct for their given problem.
- Only ask one question or offer only one suggestion at a time for the student:
    - Wait for the students response before asking a new question or offering a new suggestion.
- If the student has successfully answered the question in an optimal manner, don't continue "nit-picking" or continuning to suggest code improvements.
    - Instead, tell the student they have successfully answered the question and either encourage them to ask another one or suggest code improvements or new related concepts the student can learn or might be interested in.

##Example:

#Example Student Question:
#Find the total product of the list

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


async def generate_async_response_stream(user_question, user_code, past_user_messages_str):
    client = AsyncOpenAI(
        # api_key=os.environ['OPENAI_KEY'],
        api_key = os.environ['LAMBDA_INFERENCE_API_KEY'],
        base_url = os.environ['LAMBDA_INFERENCE_API_BASE_URL'],
    )
    # model = "gpt-4o-mini"
    model = "hermes3-405b"

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
    return {'message': 'Hello World!'}


@app.websocket("/ws_handle_chat_response")
async def websocket_handle_chat_response(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:  # Keep receiving messages in a loop
            data = await websocket.receive_json()

            user_question = data['text'].strip()
            user_code = data['user_code']
            all_user_messages_str = data['all_user_messages_str']

            # Respond to the user
            async for text in generate_async_response_stream(
                user_question=user_question,
                user_code=user_code,
                past_user_messages_str=all_user_messages_str
            ):
                if text is None:
                    await websocket.send_text('MODEL_GEN_COMPLETE')
                    break  # stop sending further text; just in case
                else:
                    await websocket.send_text(text)

    except WebSocketDisconnect:
        print("WebSocket connection closed")
        await websocket.close()


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
