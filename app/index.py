import os
from dotenv import load_dotenv, find_dotenv
ENV_FILE = find_dotenv()
load_dotenv(ENV_FILE)

import uuid
from typing import Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import docker
from celery import Celery
from celery.result import AsyncResult

# Database
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app import models, utils
from app.database import SessionLocal


app = FastAPI(
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:3000", "https://staging.companionai.dev", "https://www.companionai.dev"],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

celery_app = Celery(
    __name__,
    backend = f"{os.environ['REDIS_BACKEND_URL']}",
    broker = f"{os.environ['REDIS_BACKEND_URL']}/0",
)

## Celery Tasks ##
@celery_app.task
def execute_code_in_container(language: str, code: str):
    """
    Task to run user-submitted code inside a Docker container.
    """
    # Set up language-specific Docker image
    docker_image = {
        "python": "python:3.12-slim",
        "javascript": "node:14-slim",
        # "haskell": "haskell:latest",
        # "rust": "rust:slim"
    }.get(language)

    if not docker_image:
        raise ValueError("Unsupported language")

    language_file_extension = {
        "python": ".py",
        "javascript": ".js",
        # "haskell": ".hs",
        # "rust": ".rs"
    }
    current_file_extension = language_file_extension.get(language)
    if not current_file_extension:
        raise ValueError("Unsupported language")

    # Write the user's code to a temporary file
    host_code_dir = "/tmp"  # Directory on the host
    # code_file_name = "submission_code.py"  # Name of the file
    code_file_name = f"submission_code{current_file_extension}"
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
        "javascript": f"node {container_code_file}",
        # "haskell": f"runghc {container_code_file}",
        # "rust": f"rustc {container_code_file} -o /app/executable && /app/executable"
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
            mem_limit = "256m",
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
- Ask or Gauge their pre-requisite knowledge:
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
        api_key=os.environ['OPENAI_KEY'],
        # api_key = os.environ['LAMBDA_INFERENCE_API_KEY'],
        # base_url = os.environ['LAMBDA_INFERENCE_API_BASE_URL'],
    )
    model = "gpt-4o-mini"
    # model = "hermes3-405b"

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


@app.websocket("/ws_handle_chat_response")
async def websocket_handle_chat_response(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:  # Keep receiving messages in a loop
            data = await websocket.receive_json()

            user_question = data['text'].strip()
            user_code = data['user_code']
            all_user_messages_str = data['all_user_messages_str']

            # TODO: pass the user id for additional layer of security here
            parent_playground_object_id = data['parent_playground_object_id']
            
            parent_pg_object = db.query(models.PlaygroundObjectBase).filter(
                models.PlaygroundObjectBase.id == parent_playground_object_id,
            ).first()

            if parent_pg_object is None:
                return {'success': False, 'message': "Playground object not found.", "status_code": 404}

            # Respond to the user
            full_response_message = ""

            model_prompt = _prepate_tutor_prompt(
                user_question=user_question,
                student_code=user_code,
                student_chat_history=all_user_messages_str
            )

            async for text in generate_async_response_stream(
                user_question=user_question,
                user_code=user_code,
                past_user_messages_str=all_user_messages_str
            ):

                if text is None:

                    await websocket.send_text('MODEL_GEN_COMPLETE')
                    
                    pg_chat_conversation_object = models.PlaygroundChatConversation(
                        question = user_question,
                        prompt = model_prompt,
                        response = full_response_message,
                        code = user_code,
                        playground_parent_object_id = parent_pg_object.id
                    )
                    db.add(pg_chat_conversation_object)
                    db.commit()
                    db.refresh(pg_chat_conversation_object)
                    
                    break  # stop sending further text; just in case
                else:
                    full_response_message += text
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
    task_result = celery_app.AsyncResult(task_id)
    result_data = task_result.get()

    result_output_status = result_data['success']
    result_output_value = result_data['output']
    return {
        "result_output_status": result_output_status,
        "result_output_value": result_output_value
    }


async def get_optional_token(request: Request) -> Optional[str]:
    authorization: str = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            return token
    return None


@app.post("/save_user_run_code")
async def save_user_run_code(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_optional_token)
):

    payload = await request.json()

    code_state = payload['code_state']

    if token is not None:
        user_information_response = utils.get_user_information(
            token = token
        )        

        if user_information_response.status_code == 200:
            user_information_json_data = user_information_response.json()

            # Get user object first
            auth_zero_unique_sub_id = user_information_json_data['sub']
            associated_user_object = db.query(models.UserOAuth).filter(
                models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
            ).first()

            if associated_user_object is None:
                return {'success': False, 'message': 'Authentication Error.', 'status_code': 400}
            
            oauth_user_object_unique_id = associated_user_object.auth_zero_unique_sub_id

            # Get user object
            custom_user_object = db.query(models.CustomUser).filter(
                models.CustomUser.oauth_user_id == oauth_user_object_unique_id
            ).first()

            current_programming_language = payload.get('programming_language')

            if custom_user_object is not None:

                if 'parent_playground_object_id' in payload:
                    # TODO: handle case here where playground-object-id is already provided

                    # current_pid = payload['pid']
                    current_pid = payload['parent_playground_object_id']

                    # pg_base_object = models.PlaygroundObjectBase(id = current_pid)
                    existing_playground_base_object = db.query(models.PlaygroundObjectBase).filter(
                        models.PlaygroundObjectBase.id == current_pid,
                        models.PlaygroundObjectBase.custom_user_id == custom_user_object.id
                    ).first()

                    if existing_playground_base_object is None:
                        return {'success': False, 'message': "Not found.", 'status_code': 404}

                    pg_code_object = models.PlaygroundCode(
                        code = code_state,
                        programming_language = current_programming_language,
                        playground_parent_object_id = str(existing_playground_base_object.id)
                    )
                    db.add(pg_code_object)
                    db.commit()
                    db.refresh(pg_code_object)

                    return {"message": "Code saved", 'parent_playground_object_id': existing_playground_base_object.id, 'status_code': 200}

                else:
                    # save parent object
                    pg_base_object = models.PlaygroundObjectBase(
                        unique_name = uuid.uuid4().hex[:20],
                        custom_user_id = str(custom_user_object.id)
                    )
                    db.add(pg_base_object)
                    db.commit()
                    db.refresh(pg_base_object)
                    
                    # save code object
                    pg_code_object = models.PlaygroundCode(
                        code = code_state,
                        programming_language = current_programming_language,
                        playground_parent_object_id = str(pg_base_object.id)
                    )
                    db.add(pg_code_object)
                    db.commit() 
                    db.refresh(pg_code_object)

                    return {"message": "Code saved", 'parent_playground_object_id': pg_base_object.id, 'status_code': 200}

    else:
        user_id = payload['user_id']
        
        existing_anon_user_object = db.query(models.AnonUser).filter(models.AnonUser.user_unique_id == user_id).first()
        if existing_anon_user_object is None:
            existing_anon_user_object = models.AnonUser(
                user_unique_id = user_id
            )
            db.add(existing_anon_user_object)
            db.commit()
            db.refresh(existing_anon_user_object)

        anon_custom_user_object = db.query(models.CustomUser).filter(models.CustomUser.anon_user_id == str(existing_anon_user_object.user_unique_id)).first()
        
        if anon_custom_user_object is None:
            anon_custom_user_object = models.CustomUser(
                anon_user_id = str(user_id)
            )
            db.add(anon_custom_user_object)
            db.commit()
            db.refresh(anon_custom_user_object)
        
        parent_playground_object_id = payload.get('parent_playground_object_id', None)
        current_programming_language = payload.get('programming_language')

        if parent_playground_object_id is None:

            # if playground_parent_object is None:
            pg_parent_unique_name = uuid.uuid4().hex[:20]

            playground_parent_object = models.PlaygroundObjectBase(
                unique_name = pg_parent_unique_name,
                custom_user_id = str(anon_custom_user_object.id)
            )
            db.add(playground_parent_object)
            db.commit() 
            db.refresh(playground_parent_object)

            pg_code_object = models.PlaygroundCode(
                programming_language = current_programming_language,
                code = code_state,
                playground_parent_object_id = str(playground_parent_object.id)
            )
            db.add(pg_code_object)
            db.commit()
            db.refresh(pg_code_object)
            return {"message": "Code saved", 'parent_playground_object_id': playground_parent_object.id, 'status_code': 200}
        
        else:
            playground_parent_object = db.query(models.PlaygroundObjectBase).filter(
                models.PlaygroundObjectBase.id == str(parent_playground_object_id),
                models.PlaygroundObjectBase.custom_user_id == str(anon_custom_user_object.id)
            ).first()
            if playground_parent_object is None:
                return {"message": "Parent playground object not found", 'status_code': 404}
            else:
                pg_code_object = models.PlaygroundCode(
                    programming_language = current_programming_language,
                    code = code_state,
                    playground_parent_object_id = playground_parent_object.id
                )
                db.add(pg_code_object)
                db.commit()
                db.refresh(pg_code_object)
                return {"message": "Code saved", 'parent_playground_object_id': playground_parent_object.id, 'status_code': 200}


# Security dependency for Bearer token
bearer_scheme = HTTPBearer()

@app.post("/validate-authenticated-user")
def validate_authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_data = user_information_response.json()
        user_sub_id = user_data['sub']
        user_email = user_data['email']

        auth_user_object = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == user_sub_id
        ).first()

        if auth_user_object is None:
            auth_user_object = models.UserOAuth(
                auth_zero_unique_sub_id = user_data['sub'],
                given_name = user_data['given_name'],
                family_name = user_data['family_name'],
                full_name = user_data['name'],
                profile_picture_url = user_data['picture'],
                email = user_data['email'],
                email_verified = user_data['email_verified'],
            )
            db.add(auth_user_object)
            db.commit()
            db.refresh(auth_user_object)

        custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.oauth_user_id == user_sub_id,
        ).first()

        if custom_user_object is None:
            custom_user_object = models.CustomUser(

                oauth_user_id = auth_user_object.auth_zero_unique_sub_id,
            )
            db.add(custom_user_object)
            db.commit()
            db.refresh(custom_user_object)

        return {'success': True}

    else:
        return {'success': False, 'payload': user_information_response.json(), 'status_code': user_information_response.status_code}


# Playground Data Pydantic Model
class PlaygroundData(BaseModel):
    pid: str


@app.post("/fetch-dashboard-data")
def fetch_dashboard_data(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_information_json_data = user_information_response.json()

 # Get user object first
        auth_zero_unique_sub_id = user_information_json_data['sub']
        associated_user_objects = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).all()

        custom_user_object = None
        if len(associated_user_objects) == 0:  # Anon user trying to access a saved playground object --> return 404
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}
        else:
            # user_id = associated_user_objects[0].user_id
            oauth_user_object_unique_id = associated_user_objects[0].auth_zero_unique_sub_id

            # Get user object
            custom_user_object_item = db.query(models.CustomUser).filter(
                models.CustomUser.oauth_user_id == oauth_user_object_unique_id
            ).first()

            if custom_user_object_item is None:
                # TODO: return error here?
                raise Exception
            else:
                custom_user_object = custom_user_object_item

        if custom_user_object is not None:
            playground_object_list = db.query(models.PlaygroundObjectBase).filter(
                models.PlaygroundObjectBase.custom_user_id == custom_user_object.id
            )

            # playground_object_list = db.query(models.PlaygroundObjectBase).filter(
            #     models.PlaygroundObjectBase.custom_user_id == custom_user_object.id
            # ).order_by(desc(models.PlaygroundObjectBase.date)).all()

            rv = []
            count = 1
            for pobj in playground_object_list:

                pg_code_object = db.query(models.PlaygroundCode).filter(
                    models.PlaygroundCode.playground_parent_object_id == pobj.id
                ).order_by(models.PlaygroundCode.created_date.desc()).first()

                number_of_chat_messages = db.query(models.PlaygroundChatConversation).filter(
                    models.PlaygroundChatConversation.playground_parent_object_id == pobj.id
                ).count()

                rv.append({
                    'id': pobj.id,
                    'count': count,
                    'code_file_name': f"Code File #{count}",
                    'number_of_chat_messages': number_of_chat_messages,
                    'name': pobj.unique_name,
                    'programming_language': pg_code_object.programming_language,
                    'created_date': pobj.created_at.date(),
                    "updated_date": pobj.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                })
                count += 1

            rv.reverse()

            return {
                'success': True,
                'playground_object_list': rv
            }


@app.post("/fetch-playground-data")
def fetch_playground_data(
    request: Request,
    post_data: PlaygroundData,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_information_json_data = user_information_response.json()
        playground_object_id = post_data.pid

        # Get user object first
        auth_zero_unique_sub_id = user_information_json_data['sub']
        associated_user_objects = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).all()

        custom_user_object = None
        if len(associated_user_objects) == 0:  # Anon user trying to access a saved playground object --> return 404
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}
        else:
            # user_id = associated_user_objects[0].user_id
            oauth_user_object_unique_id = associated_user_objects[0].auth_zero_unique_sub_id

            # Get user object
            custom_user_object_item = db.query(models.CustomUser).filter(
                models.CustomUser.oauth_user_id == oauth_user_object_unique_id
            ).first()

            if custom_user_object_item is None:
                # TODO: return error here?
                raise Exception
            else:
                custom_user_object = custom_user_object_item

        if custom_user_object is not None:
            # Get playground object with pid and user information
            playground_obj = db.query(models.PlaygroundObjectBase).filter(
                models.PlaygroundObjectBase.id == playground_object_id,
                models.PlaygroundObjectBase.custom_user_id == custom_user_object.id
            ).first()

            if playground_obj is None:
                return {'success': False, 'message': 'Not Found.', 'status_code': 404}
            
            # Get most recent code for playground object
            pg_code_object = db.query(models.PlaygroundCode).filter(
                # models.PlaygroundCode.playground_object_id == pg_object.id
                models.PlaygroundCode.playground_parent_object_id == playground_obj.id
            ).order_by(models.PlaygroundCode.created_date.desc()).first()

            # TODO: get chat messages
            pg_chat_object_list = db.query(models.PlaygroundChatConversation).filter(
                models.PlaygroundChatConversation.playground_parent_object_id == playground_obj.id
            ).all()

            final_chat_messages_rv_list = [{
                'id': None,
                'text': """Welcome! 😄 I'm Companion, your personal programming tutor.

If you are running into a problem such as a bug in your code, a LeetCode problem, or need help understanding a concept, ask me and I will be more than happy to help.""",
                'sender': "bot",
                'complete': True
            }]
            for ch_obj in pg_chat_object_list:
                # final_chat_messages_rv_list.append({
                #     'id': ch_obj.id,
                #     'question': ch_obj.question,
                #     'response': ch_obj.response,
                # })
                
                final_chat_messages_rv_list.append({
                    'id': ch_obj.id,
                    'text': ch_obj.question,
                    'sender': 'user',
                    'complete': True
                })

                final_chat_messages_rv_list.append({
                    'id': ch_obj.id,
                    'text': ch_obj.response,
                    'sender': 'bot',
                    'complete': True
                })

            return {
                'success': True,
                'playground_object_id': playground_obj.id,
                'programming_language': pg_code_object.programming_language,
                'code': pg_code_object.code,
                'chat_messages': final_chat_messages_rv_list
            }


