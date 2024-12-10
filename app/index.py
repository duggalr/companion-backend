import os
from dotenv import load_dotenv, find_dotenv
ENV_FILE = find_dotenv()
load_dotenv(ENV_FILE)

import uuid
from typing import Optional
from pydantic import BaseModel
from openai import AsyncOpenAI, OpenAI
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
        # "javascript": "node:14-slim",
        # "haskell": "haskell:latest",
        # "rust": "rust:slim"
    }.get(language)

    if not docker_image:
        raise ValueError("Unsupported language")

    language_file_extension = {
        "python": ".py",
        # "javascript": ".js",
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
        # "javascript": f"node {container_code_file}",
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
def _prepate_tutor_prompt(user_current_problem_name, user_current_problem_text, user_question, student_code, student_chat_history):
    # - For example, if the student asks about a specific data structure or algorithm, try to understand their understanding of the underlying concepts like arrays, linked lists, stacks, queues, trees, graphs, and recursion.
    prompt = """##Task:
You will be assisting a student, who will be asking questions on a specific Python Programming Problem.
Your will be their upbeat, encouraging tutor.
- Even though you are encouraging and upbeat, maintain a natural conversation flow. Don't overcompliment in each message. Keep it natural like a good tutor.
Your primary goal is to guide and mentor them, helping them solve their problem effectively, but also to become a great individual thinker. Please adhere to these guidelines. Further instructions are provided below. Also, an example is provided below.
- In addition, if the student has correctly solved the problem, end the conversation.
- Do not try to make the conversation going along, especially when the student has already successfully solved the problem.
- Instead, ask the student if they have any other questions or other concepts/problems they would like to explore.
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

##Student Current Working Problem:
Name: {user_current_problem_name}

Question: {user_current_problem_text}


##Student Chat Message:
{question}

##Student Code:
{student_code}

##Your Answer:
"""
    
    prompt = prompt.format(
        question=user_question,
        student_code=student_code,
        student_chat_history=student_chat_history,
        user_current_problem_name=user_current_problem_name,
        user_current_problem_text=user_current_problem_text,
    )
    print(prompt)
    return prompt



def _prepare_general_tutor_prompt(user_question, student_chat_history):
    prompt = """##Instructions:
You will be a personal learning assistant primarily for students or individuals who are learning new concepts and fields.
Be as resourceful to them as possible and provide them with as much guidance and help.

No Direct Answers:
- If a student comes to you with a specific question they are working on and need help with it, do not provide them with any sort of direct answer.
- Instead, like a great tutor, provide the student with hints, potentially through precise examples that will help guide their thinking.
- Encourage problem solving to ensure the student is able to think through the problem on their own.
- For specific problems the student is working on, especially programming related, don't provide pseudocode or direct code solutions.
- Providing code or pseudocode for smaller, specific parts of their problem is okay but in general, force the student to think through the problem on their own.
- Rather, provide the student with precise examples and hints, that will help guide their thinking.
- Under no circumstance should you provide the student a direct answer.

Exploratory Questions:
- If a student comes to you with a more exploratory question, like "what is xyz", or "why is xyz useful", or "how do I learn xyz",
be as detailed as possible in your response. Provide them with solid, relevant information, along with precise examples if applicable.
- Understand their interests or objectives and really help fulfill their intellectual curiosity.
- If relevant and applicable, help the individual develop their own syllabus, lesson plan, questions, quizzes, so they can get a deep understanding of their material.

Based on the conversation, try to always ask meaningful follow-up questions to the individual. 
This is a great way to foster a more engaging conversation, and help the individual gain a more deeper understanding of the material they are trying to learn.
However, if you feel the student has received the information they need and there is no meaningful follow-up question you can think of, please close out the conversation by thanking the student and telling them they can ask any other questions if they wish.

##Previous Chat History with Student:
{previous_chat_history_st}

##Student Question:
{question}

##Your Answer:
"""
    prompt = prompt.format(
        question=user_question,
        previous_chat_history_st=student_chat_history
    )
    return prompt



async def generate_async_response_stream(prompt):
    client = AsyncOpenAI(
        api_key=os.environ['OPENAI_KEY'],
        # api_key = os.environ['LAMBDA_INFERENCE_API_KEY'],
        # base_url = os.environ['LAMBDA_INFERENCE_API_BASE_URL'],
    )
    model = "gpt-4o-mini"
    # model = "hermes3-405b"

    # prompt = _prepate_tutor_prompt(
    #     user_question = user_question,
    #     student_code = user_code,
    #     student_chat_history = past_user_messages_str
    # )
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


def _generate_sync_ai_response(prompt):
    client = OpenAI(
        api_key=os.environ['OPENAI_KEY'],
    )
    model = "gpt-4o-mini"
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        model=model,
        response_format={ "type": "json_object" }
    )    
    return response




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
            user_current_problem_name, user_current_problem_text = data['current_problem_name'], data['current_problem_question']

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
                user_current_problem_name = user_current_problem_name,
                user_current_problem_text = user_current_problem_text,
                user_question=user_question,
                student_code=user_code,
                student_chat_history=all_user_messages_str
            )

            async for text in generate_async_response_stream(
                prompt = model_prompt
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

            # # if playground_parent_object is None:
            # pg_parent_unique_name = uuid.uuid4().hex[:20]

            playground_parent_object = models.PlaygroundObjectBase(
                # unique_name = pg_parent_unique_name,
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

class AnonUserRequestData(BaseModel):
    anon_user_id: str

class GeneralTutorConversationRequestData(BaseModel):
    gt_object_id: str

class ChangeGeneralTutorConversationRequestData(BaseModel):
    gt_object_id: str
    conversation_name: str

class ChangeCodeConversationRequestData(BaseModel):
    current_conversation_id: str
    new_conversation_name: str

class GenerateTestCasesQuestoinData(BaseModel):
    question_name: str
    question_text: str



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

                if pobj.unique_name is not None:
                    code_file_name = pobj.unique_name
                else:
                    code_file_name = f"Code File #{count}"
                
                rv.append({
                    'id': pobj.id,
                    'count': count,
                    'code_file_name': code_file_name,
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




@app.post("/create-anon-user")
def create_anon_user(
    request: Request,
    data: AnonUserRequestData,
    db: Session = Depends(get_db)
):
    anon_user_id = data.anon_user_id
    print(f"anon-user-id: {anon_user_id}")

    existing_anon_user_object = models.AnonUser(
        user_unique_id = anon_user_id
    )
    db.add(existing_anon_user_object)
    db.commit()
    db.refresh(existing_anon_user_object)

    anon_custom_user_object = models.CustomUser(
        anon_user_id = str(anon_user_id)
    )
    db.add(anon_custom_user_object)
    db.commit()
    db.refresh(anon_custom_user_object)

    return {"success": True}


@app.post("/validate-anon-user")
def validate_anon_user(
    request: Request,
    data: AnonUserRequestData,
    db: Session = Depends(get_db)
):
    anon_user_id = data.anon_user_id
    print(f"anon-user-id: {anon_user_id}")

    anon_user_object = db.query(models.CustomUser).filter(
        models.CustomUser.anon_user_id == anon_user_id
    ).first()

    if anon_user_object is None:  # create anon user
        existing_anon_user_object = models.AnonUser(
            user_unique_id = anon_user_id
        )
        db.add(existing_anon_user_object)
        db.commit()
        db.refresh(existing_anon_user_object)

        anon_custom_user_object = models.CustomUser(
            anon_user_id = str(anon_user_id)
        )
        db.add(anon_custom_user_object)
        db.commit()
        db.refresh(anon_custom_user_object)
    else:
        return {'success': True}


@app.post("/create-general-tutor-parent-object")
def create_general_tutor_parent_object(
    request: Request,
    # data: AnonUserRequestData,
    data: Optional[AnonUserRequestData] = None,
    token: Optional[str] = Depends(get_optional_token),
    db: Session = Depends(get_db)
):
    if token is not None:
        # handle authenticated state
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

            print(f"Custom User Object: {custom_user_object}")

            general_tutor_parent_object = models.GeneralTutorParentObject(
                custom_user_id = custom_user_object.id
            )
            db.add(general_tutor_parent_object)
            db.commit()
            db.refresh(general_tutor_parent_object)

            return {
                'general_tutor_parent_object_id': general_tutor_parent_object.id
            }

    else:
        # unauthenticated state
        anon_user_id = data.anon_user_id
        
        custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.anon_user_id == anon_user_id
        ).first()

        if custom_user_object is None:
            return {'success': False, 'message': 'User not found.'}

        general_tutor_parent_object = models.GeneralTutorParentObject(
            custom_user_id = custom_user_object.id
        )
        db.add(general_tutor_parent_object)
        db.commit()
        db.refresh(general_tutor_parent_object)

        return {
            'general_tutor_parent_object_id': general_tutor_parent_object.id
        }


@app.websocket("/ws_general_tutor_chat")
async def websocket_general_tutor_handle(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:  # Keep receiving messages in a loop
            data = await websocket.receive_json()

            print('received_data:', data)

            user_message = data['text'].strip()
            all_past_user_messages = data['all_past_chat_messages'].strip()
            general_tutor_parent_object_id = data['general_tutor_object_id']

            # TODO: pass the user id for additional layer of security here
            general_tutor_parent_object = db.query(models.GeneralTutorParentObject).filter(
                models.GeneralTutorParentObject.id == general_tutor_parent_object_id,
            ).first()

            if general_tutor_parent_object is None:
                return {'success': False, 'message': "Object not found.", "status_code": 404}
            
            # Respond to the user
            full_response_message = ""

            # TODO: finalize the general_tutor_prompt 
            gt_model_prompt = _prepare_general_tutor_prompt(
                user_question = user_message,
                student_chat_history = all_past_user_messages
            )

            async for text in generate_async_response_stream(
                prompt = gt_model_prompt,
            ):
                if text is None:
                    await websocket.send_text('MODEL_GEN_COMPLETE')
                    gt_chat_conversation_object = models.GeneralTutorChatConversation(
                        user_message = user_message,
                        prompt = gt_model_prompt,
                        model_response = full_response_message,
                        general_tutor_parent_object_id = general_tutor_parent_object.id,
                    )
                    db.add(gt_chat_conversation_object)
                    db.commit()
                    db.refresh(gt_chat_conversation_object)
                    
                    break  # stop sending further text; just in case
                else:
                    full_response_message += text
                    await websocket.send_text(text)

    except WebSocketDisconnect:
        print("WebSocket connection closed")
        await websocket.close()


@app.post("/fetch-general-tutor-conversation")
def fetch_general_tutor_conversation(
    request: Request,
    data: GeneralTutorConversationRequestData,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    
    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_information_json_data = user_information_response.json()

        # Get user object first
        auth_zero_unique_sub_id = user_information_json_data['sub']
        user_auth_zero_object = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).first()

        if user_auth_zero_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}
        
        associated_custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.oauth_user_id == user_auth_zero_object.auth_zero_unique_sub_id
        ).first()

        if associated_custom_user_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}

        # Fetch General Tutor Information
        general_tutor_parent_object_id = data.gt_object_id
        general_tutor_parent_object = db.query(models.GeneralTutorParentObject).filter(
            models.GeneralTutorParentObject.id == general_tutor_parent_object_id,
        ).first()

        if general_tutor_parent_object is None:
            return {'success': False, 'error': "Object not found."}

        gt_chat_conversation_objects = db.query(models.GeneralTutorChatConversation).filter(
            models.GeneralTutorChatConversation.general_tutor_parent_object_id == general_tutor_parent_object.id,
        ).all()

        final_chat_messages_rv_list = [{
            'id': None,
            'text': """Welcome! 😄 I'm Companion, your general tutor.
        
Feel free to ask me about anything you would like to learn, whether that's a problem you are working on, or a concept that need's further explaining...""",
            'sender': "bot",
            'complete': True
        }]

        for ch_obj in gt_chat_conversation_objects:
            final_chat_messages_rv_list.append({
                'id': ch_obj.id,
                'text': ch_obj.user_message,
                'sender': 'user',
                'complete': True
            })
            final_chat_messages_rv_list.append({
                'id': ch_obj.id,
                'text': ch_obj.model_response,
                'sender': 'bot',
                'complete': True
            })

        return {
            'success': True,
            'gt_object_id': general_tutor_parent_object_id,
            'chat_messages': final_chat_messages_rv_list

            # 'playground_object_id': playground_obj.id,
            # 'programming_language': pg_code_object.programming_language,
            # 'code': pg_code_object.code,
            # 'chat_messages': final_chat_messages_rv_list
        }


@app.post("/fetch_all_user_gt_conversations")
def fetch_all_user_gt_conversations(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    
    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_information_json_data = user_information_response.json()

        # Get user object first
        auth_zero_unique_sub_id = user_information_json_data['sub']
        user_auth_zero_object = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).first()

        if user_auth_zero_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}
        
        associated_custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.oauth_user_id == user_auth_zero_object.auth_zero_unique_sub_id
        ).first()

        if associated_custom_user_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}

        user_gt_objects = db.query(models.GeneralTutorParentObject).filter(
            models.GeneralTutorParentObject.custom_user_id == associated_custom_user_object.id,
        ).order_by(models.GeneralTutorParentObject.updated_at.desc()).all()

        final_rv = []
        c = 1
        for obj in user_gt_objects:
            # # TOOD: 
            # print('Conv-Name:', obj.unique_name)
            if obj.unique_name is not None:
                final_rv.append({
                    'object_id': obj.id,
                    'name': obj.unique_name.strip(),
                })
            else:
                final_rv.append({
                    'object_id': obj.id,
                    'name': f"Conversation #{c}",
                })
            c += 1

        return {
            'success': True,
            'all_gt_objects': final_rv
        }


@app.post("/change_gt_conversation_name")
def change_gt_conversation_name(
    request: Request,
    data: ChangeGeneralTutorConversationRequestData,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):

    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_information_json_data = user_information_response.json()

        # Get user object first
        auth_zero_unique_sub_id = user_information_json_data['sub']
        user_auth_zero_object = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).first()

        if user_auth_zero_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}
        
        associated_custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.oauth_user_id == user_auth_zero_object.auth_zero_unique_sub_id
        ).first()

        if associated_custom_user_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}

        # Get current GT conversation object
        gt_object_id = data.gt_object_id
        gt_new_conversation_name = data.conversation_name

        gt_object = db.query(models.GeneralTutorParentObject).filter(
            models.GeneralTutorParentObject.id == gt_object_id,
            models.GeneralTutorParentObject.custom_user_id == associated_custom_user_object.id,
        ).first()

        # Check if the object exists before modifying it
        if gt_object:
            gt_new_conversation_name = gt_new_conversation_name.strip()
            gt_object.unique_name = gt_new_conversation_name
            db.commit()
            db.refresh(gt_object)
            return {
                'success': True,
            }
        else:
            return {'success': False}
        

@app.post("/change_pg_code_name")
def change_pg_code_name(
    request: Request,
    data: ChangeCodeConversationRequestData,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):

    token = credentials.credentials
    user_information_response = utils.get_user_information(
        token = token
    )

    if user_information_response.status_code == 200:
        user_information_json_data = user_information_response.json()

        # Get user object first
        auth_zero_unique_sub_id = user_information_json_data['sub']
        user_auth_zero_object = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).first()

        if user_auth_zero_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}
        
        associated_custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.oauth_user_id == user_auth_zero_object.auth_zero_unique_sub_id
        ).first()

        if associated_custom_user_object is None:
            return {'success': False, 'message': 'Not Found.', 'status_code': 404}

        # Get current GT conversation object
        pg_object_id = data.current_conversation_id
        pg_new_conversation_name = data.new_conversation_name.strip()

        pg_object = db.query(models.PlaygroundObjectBase).filter(
            models.PlaygroundObjectBase.id == pg_object_id,
            models.PlaygroundObjectBase.custom_user_id == associated_custom_user_object.id,
        ).first()

        if pg_object:
            pg_object.unique_name = pg_new_conversation_name
            db.commit()
            db.refresh(pg_object)
            return {
                'success': True,
            }
        else:
            return {'success': False}


# @app.post("/generate_new_question_testcases")
# def generate_new_testcases(
@app.post("/update_user_question")
def save_or_update_user_question(
    request: Request,
    data: GenerateTestCasesQuestoinData,
    db: Session = Depends(get_db)
):

    unique_question_id = data.question_id
    question_name = data.question_name.strip()
    question_text = data.question_text.strip()

    prompt = """## Instructions:
For the given question below, your task is to generate:
- 3 Distinct Input / Output Examples with a 1-2 line description for each example to be shown to the user, to help them better understand the question.
- 10 extremely well-thought and diverse test-cases, to actually test the user's code on submission. These won't be shown to the user, but meant to test the correctness of the user's code/submission.

Return the following JSON dictionary below, with the specified format below.
- For cases where you need to generate an input / output dictionary containing multiple parameters or value, please encapsulate the dictionary as a string.

## Example Output:
{
    "input_output_example_list": [{"input": "...", "output": "..."}, ...],
    "test_case_list": [{"input": "...", "output": "..."}, ...]
}

## Data:
"""

    prompt += f"""Question: {question_text}

## Output:
"""
    print(prompt)

    response = _generate_sync_ai_response(prompt)
    print(f"Response:", response)

    import json

    response_json_dict = json.loads(response.choices[0].message.content)
    print(response_json_dict)

    question_input_output_example_list = response_json_dict['input_output_example_list']
    question_test_case_list = response_json_dict['test_case_list']

    if unique_question_id is None:
        pg_question_object = models.PlaygroundQuestion(
            name = question_name,
            text = question_text,
            example_io_list = question_input_output_example_list,
            test_case_list = question_test_case_list
        )
        db.add(pg_question_object)
        db.commit()
        db.refresh(pg_question_object)

        final_rv = {
            'success': True,
            'unique_question_id': unique_question_id,
            'question_name': question_name,
            'question_text': question_text,
            'example_io_list': question_input_output_example_list
        }
        return final_rv

    else:
        pg_question_object = db.query(models.PlaygroundQuestion).filter(
            models.PlaygroundQuestion.id == unique_question_id
        ).first()

        if pg_question_object:
            pg_question_object.name = question_name
            pg_question_object.text = question_text
            pg_question_object.example_io_list = question_input_output_example_list
            pg_question_object.test_case_list = question_test_case_list
            db.commit()

            final_rv = {
                'success': True,
                'unique_question_id': unique_question_id,
                'question_name': question_name,
                'question_text': question_text,
                'example_io_list': question_input_output_example_list
            }
            return final_rv

        else:
            return {'success': False, 'message': "Question object not found."}

    # final_rv = {
    #     'success': True,
    #     'model_response': response_json_dict
    # }
    # return final_rv

    # async for text in generate_async_response_stream(
    #     prompt = prompt,
    # ):
    #     if text is None:
    #         await websocket.send_text('MODEL_GEN_COMPLETE')
    #         break  # stop sending further text; just in case
    #     else:
    #         await websocket.send_text(text)



from sqlalchemy.sql.expression import func
import ast

@app.post("/get_random_initial_pg_question")
def get_random_initial_pg_question(
    request: Request,
    db: Session = Depends(get_db)
):
    random_pg_q_object = db.query(models.PlaygroundQuestion).order_by(func.random()).first()
    random_pg_q_object_dict = {
        # column.name: getattr(random_pg_q_object, column.name)
        # for column in random_pg_q_object.__table__.columns
        'question_id': random_pg_q_object.id,
        'name': random_pg_q_object.name,
        'text': random_pg_q_object.text,
        'starter_code': random_pg_q_object.starter_code,
        'example_io_list': ast.literal_eval(random_pg_q_object.example_io_list)
    }
    return random_pg_q_object_dict


class UserCodeSubmission(BaseModel):
    pg_object_id: str
    user_code: str
    question_id: str

@app.post("/submit_user_code")
def handle_user_code_submission(
    request: Request,
    data: UserCodeSubmission,
    db: Session = Depends(get_db)
):
    print('code-submission-data:', data)

    pg_object_id = data.pg_object_id
    question_id = data.question_id
    user_code = data.user_code

    pg_question_object = db.query(models.PlaygroundQuestion).filter(
        models.PlaygroundQuestion.id == question_id
    ).first()

    q_test_cases = ast.literal_eval(pg_question_object.test_case_list)
    print('question-test-cases:', q_test_cases)
    # TODO: go through each test case




# class GenerateTestCasesQuestoinData(BaseModel):
#     question_name: str
#     question_text: str

# @app.websocket("/ws_generate_new_question_testcases")
# async def websocket_generate_new_question_testcases(websocket: WebSocket, db: Session = Depends(get_db)):
#     await websocket.accept()
#     try:
#         while True:  # Keep receiving messages in a loop
#             data = await websocket.receive_json()
#             print('received_data:', data)

#             action_type = data['type']
#             if action_type == 'generate_test_case':
#                 question_name = data['question_name'].strip()
#                 question_text = data['question_text'].strip()

#                 prompt = """## Instructions:
# Your task is to generate example input / output examples, given the question below.
# Return a list, with 3 JSON dictionaries showing input and output examples for the question.

# ## Example Output:
# [{"input": "...", "output": "..."}, ...]

# ## Data:
# """

#                 prompt += f"""Question: {question_text}

# ## Output:
# """
#                 print(prompt)

#                 # TODO: 

#                 async for text in generate_async_response_stream(
#                     prompt = prompt,
#                 ):
#                     if text is None:
#                         await websocket.send_text('MODEL_GEN_COMPLETE')
#                         break  # stop sending further text; just in case
#                     else:
#                         await websocket.send_text(text)
        
#             # user_message = data['text'].strip()
#             # all_past_user_messages = data['all_past_chat_messages'].strip()
#             # general_tutor_parent_object_id = data['general_tutor_object_id']

#             # # TODO: pass the user id for additional layer of security here
#             # general_tutor_parent_object = db.query(models.GeneralTutorParentObject).filter(
#             #     models.GeneralTutorParentObject.id == general_tutor_parent_object_id,
#             # ).first()

#             # if general_tutor_parent_object is None:
#             #     return {'success': False, 'message': "Object not found.", "status_code": 404}
            
#             # # Respond to the user
#             # full_response_message = ""

#             # # TODO: finalize the general_tutor_prompt 
#             # gt_model_prompt = _prepare_general_tutor_prompt(
#             #     user_question = user_message,
#             #     student_chat_history = all_past_user_messages
#             # )

#             # async for text in generate_async_response_stream(
#             #     prompt = gt_model_prompt,
#             # ):
#             #     if text is None:
#             #         await websocket.send_text('MODEL_GEN_COMPLETE')
#             #         gt_chat_conversation_object = models.GeneralTutorChatConversation(
#             #             user_message = user_message,
#             #             prompt = gt_model_prompt,
#             #             model_response = full_response_message,
#             #             general_tutor_parent_object_id = general_tutor_parent_object.id,
#             #         )
#             #         db.add(gt_chat_conversation_object)
#             #         db.commit()
#             #         db.refresh(gt_chat_conversation_object)
                    
#             #         break  # stop sending further text; just in case
#             #     else:
#             #         full_response_message += text
#             #         await websocket.send_text(text)

#     except WebSocketDisconnect:
#         print("WebSocket connection closed")
#         await websocket.close()
