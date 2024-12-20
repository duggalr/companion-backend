import os
from typing import Optional, Generator
import ast
import json
from json import JSONDecodeError
import docker
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.orm import Session

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import SessionLocal
from app.llm import prompts, openai_wrapper
from app.models import UserOAuth, CustomUser, InitialPlaygroundQuestion, UserCreatedPlaygroundQuestion, PlaygroundCode, UserCreatedPlaygroundQuestion, PlaygroundChatConversation, LandingPageEmail
from app.pydantic_schemas import NotRequiredAnonUserSchema, RequiredAnonUserSchema, UpdateQuestionSchema, CodeExecutionRequestSchema, SaveCodeSchema, SaveLandingPageEmailSchema, FetchQuestionDetailsSchema, ValidateAuthZeroUserSchema
from app.config import settings
from app.utils import create_anon_user_object, get_anon_custom_user_object, _get_random_initial_pg_question, get_user_object, get_optional_token
from app.llm.prompt_utils import _prepate_tutor_prompt
from app.scripts.verify_auth_zero_jwt import verify_jwt


app = FastAPI(
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json",
    debug=True
)

# Dependency for database
def get_db() -> Generator[Session, None, None]:
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database connection failed")
    finally:
        db.close()

# Open Wrapper
def get_openai_wrapper() -> openai_wrapper.OpenAIWrapper:
    return openai_wrapper.OpenAIWrapper(
        api_key=settings.openai_key,
        model="gpt-4o-mini"
    )

# Initialize Celery
celery_app = Celery(
    __name__,
    backend = f"{os.environ['REDIS_BACKEND_URL']}",
    broker = f"{os.environ['REDIS_BACKEND_URL']}/0",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security dependency for Bearer token
bearer_scheme = HTTPBearer()


## Views

@app.post("/save_landing_page_email")
def save_landing_page_email(
    data: SaveLandingPageEmailSchema,
    db: Session = Depends(get_db)
):
    user_email = data.email.strip()
    lp_email_object = LandingPageEmail(
        email = user_email
    )
    db.add(lp_email_object)
    db.commit()
    db.refresh(lp_email_object)

    return {'success': True}


@app.post("/get_number_of_lp_email_submissions")
def get_number_of_registered_emails(
    db: Session = Depends(get_db)
):
    number_of_email_submissions = db.query(LandingPageEmail).count()
    return {
        'success': True,
        'number_of_email_submissions': number_of_email_submissions
    }


@app.post("/create-anon-user")
def create_anon_user(
    data: RequiredAnonUserSchema,
    db: Session = Depends(get_db)
):
    anon_user_id = data.user_id
    custom_user_object_id = create_anon_user_object(
        anon_user_id = anon_user_id,
        db = db
    )
    return {
        'success': True,
        'custom_user_object_dict': custom_user_object_id
    }


@app.post("/validate-anon-user")
def validate_anon_user(
    data: RequiredAnonUserSchema,
    db: Session = Depends(get_db)
):
    anon_user_id = data.user_id
    custom_user_object_id = create_anon_user_object(
        anon_user_id = anon_user_id,
        db = db
    )
    return {
        'success': True,
        'custom_user_object_dict': custom_user_object_id
    }


@app.post("/validate-authenticated-user")
def validate_authenticated_user(
    data: ValidateAuthZeroUserSchema,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):

    token = credentials.credentials
    token_info_dict = verify_jwt(
        token = token
    )
    if 'error' in token_info_dict:
        raise HTTPException(status_code=500, detail=token_info_dict['error'])

    auth_zero_unique_sub_id = token_info_dict['sub']    
    auth_user_object = db.query(UserOAuth).filter(
        UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
    ).first()

    if auth_user_object is None:
        auth_user_object = UserOAuth(
            auth_zero_unique_sub_id = auth_zero_unique_sub_id,
            given_name = data.given_name,
            family_name = data.family_name,
            full_name = data.full_name,
            profile_picture_url = data.profile_picture_url,
            email = data.email,
            email_verified = data.email_verified,
        )
        db.add(auth_user_object)
        db.commit()
        db.refresh(auth_user_object)

    custom_user_object = db.query(CustomUser).filter(
        CustomUser.oauth_user_id == auth_zero_unique_sub_id,
    ).first()

    if custom_user_object is None:
        custom_user_object = CustomUser(
            oauth_user_id = auth_user_object.auth_zero_unique_sub_id,
        )
        db.add(custom_user_object)
        db.commit()
        db.refresh(custom_user_object)

    return {'success': True}


@app.post("/get_random_initial_pg_question")
def get_random_initial_playground_question(
    data: NotRequiredAnonUserSchema,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_optional_token)
):
    current_custom_user_object = get_user_object(
        db = db,
        user_id = data.user_id,
        token = token
    )
    if current_custom_user_object is None:
        raise HTTPException(status_code=400, detail="User object not found.")

    # Get Random Question Object
    random_initial_question_object = _get_random_initial_pg_question(
        db = db
    )

    to_return = {
        # 'question_id': random_initial_question_object.id,
        'name': random_initial_question_object.name,
        'text': random_initial_question_object.text,
        'starter_code': random_initial_question_object.starter_code,
        'example_io_list': ast.literal_eval(random_initial_question_object.example_io_list)
    }
    return {
        'success': True,
        'data': to_return
    }


@app.post("/update_user_question")
def update_user_question(
    data: UpdateQuestionSchema,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_optional_token),
    op_ai_wrapper: openai_wrapper.OpenAIWrapper = Depends(get_openai_wrapper)
):
    anon_user_id = data.user_id
    authenticated_user_object = get_user_object(
        db = db,
        user_id = anon_user_id,
        token = token
    )

    pg_question_object = _get_or_create_user_question_object(
        db = db,
        data = SaveCodeSchema(**{
            'user_id': None,
            'question_id': data.question_id,
            'question_name': data.question_name,
            'question_text': data.question_text,
            'example_input_output_list': data.example_input_output_list,
            'code': ''
        }),
        custom_user_object = authenticated_user_object
    )

   # Generate AI Response
    try:
        prompt = f"{prompts.GENERATE_INPUT_OUTPUT_EXAMPLE_PROMPT}Question: {data.question_text.strip()}\n\n## Output:\n"
        ai_response = op_ai_wrapper.generate_sync_response(
            prompt = prompt
        )
        ai_response_json_dict = json.loads(ai_response.choices[0].message.content)
    except (KeyError, JSONDecodeError):
        raise HTTPException(status_code=500, detail="Invalid AI response format.")

    # Convert to JSON
    question_input_output_example_list_string = str(ai_response_json_dict['input_output_example_list'])
    question_input_output_example_list_json_representation = json.dumps(ai_response_json_dict['input_output_example_list'])

    # Update Question Object
    pg_question_object.name = data.question_name
    pg_question_object.text = data.question_text
    pg_question_object.example_io_list = question_input_output_example_list_string
    db.commit()
    db.refresh(pg_question_object)

    final_rv = {
        'unique_question_id': pg_question_object.id,
        'question_name': data.question_name,
        'question_text': data.question_text,
        'example_io_list': question_input_output_example_list_json_representation
    }
    return {
        'success': True,
        'data': final_rv
    }


## Celery Tasks ##
@celery_app.task
def execute_code_in_container(language: str, code: str):
    """
    Task to run user-submitted code inside a Docker container.
    """
    # Set up language-specific Docker image
    docker_image = {
        "python": "python:3.12-slim",
    }.get(language)

    if not docker_image:
        raise ValueError("Unsupported language")

    language_file_extension = {
        "python": ".py",
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


@app.post("/execute_user_code")
async def execute_code(
    request: CodeExecutionRequestSchema
):
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
async def get_status(
    task_id: str
):
    task_result = AsyncResult(task_id)
    return {"task_id": task_id, "status": task_result.status}


@app.get("/result/{task_id}")
def get_result(
    task_id: str
):
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


def _get_or_create_user_question_object(db: Session, data: SaveCodeSchema, custom_user_object: CustomUser):
    existing_pg_question_object = None
    if data.question_id is not None:
        existing_pg_question_object = db.query(UserCreatedPlaygroundQuestion).filter(
            UserCreatedPlaygroundQuestion.id == data.question_id,
            UserCreatedPlaygroundQuestion.custom_user_id == custom_user_object.id 
        ).first()
        if not existing_pg_question_object:
            raise HTTPException(status_code=404, detail="Question object not found or unauthorized.")
    else:
        existing_pg_question_object = UserCreatedPlaygroundQuestion(
            name = data.question_name,
            text = data.question_text,
            example_io_list = str(data.example_input_output_list),
            custom_user_id = custom_user_object.id
        )
        db.add(existing_pg_question_object)
        db.commit()
        db.refresh(existing_pg_question_object)
    
    return existing_pg_question_object


@app.post("/save_user_question")
def save_user_question(
    data: UpdateQuestionSchema,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_optional_token),
):
    custom_user_object = get_user_object(
        db,
        data.user_id,
        token
    )

    pg_question_object = UserCreatedPlaygroundQuestion(
        name = data.question_name,
        text = data.question_text,
        example_io_list = str(data.example_input_output_list),
        custom_user_id = custom_user_object.id
    )
    db.add(pg_question_object)
    db.commit()
    db.refresh(pg_question_object)

    return {
        'success': True,
        'data': {'question_id': pg_question_object.id}
    }



@app.post("/save_user_code")
def save_user_code(
    data: SaveCodeSchema,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_optional_token),
):
    # TODO: need to add a verification check here to see if the user who is requesting to save the code on the question can actually do so..

    custom_user_object = get_user_object(
        db,
        data.user_id,
        token
    )
    question_object = _get_or_create_user_question_object(
        db = db,
        data = data,
        custom_user_object = custom_user_object
    )
    # # question_object = db.query(UserCreatedPlaygroundQuestion).filter(
    # #     UserCreatedPlaygroundQuestion.id == data.question_id,
    # #     UserCreatedPlaygroundQuestion.custom_user_id == custom_user_object.id   
    # # ).first()
    # # if question_object is None:
    # #     raise HTTPException(status_code=404, detail="Question not found.")

    # user_id = data.user_id
    # question_id = data.question_id

    current_code = data.code
    pg_code_object = PlaygroundCode(
        programming_language = 'python',
        code = current_code,
        question_object_id = question_object.id
    )
    db.add(pg_code_object)
    db.commit()
    db.refresh(pg_code_object)

    return {
        'success': True,
        'data': {'question_id': question_object.id}
    }


## Websocket 

@app.websocket("/ws_handle_chat_response")
async def websocket_handle_chat_response(
    websocket: WebSocket,
    db: Session = Depends(get_db),
    op_ai_wrapper: openai_wrapper.OpenAIWrapper = Depends(get_openai_wrapper)
):
    await websocket.accept()
    try:
        while True:  # Keep receiving messages in a loop
            data = await websocket.receive_json()

            user_question = data['text'].strip()
            user_code = data['user_code']
            all_user_messages_str = data['all_user_messages_str']
            user_current_problem_name, user_current_problem_text = data['current_problem_name'], data['current_problem_question']

            parent_question_object_id = data['parent_question_object_id']
            parent_question_object = db.query(UserCreatedPlaygroundQuestion).filter(
                UserCreatedPlaygroundQuestion.id == parent_question_object_id
            ).first()

            if parent_question_object is None:
                return {'success': False, 'message': "Question object not found.", "status_code": 404}

            # Respond to the user
            full_response_message = ""

            model_prompt = _prepate_tutor_prompt(
                user_current_problem_name = user_current_problem_name,
                user_current_problem_text = user_current_problem_text,
                user_question=user_question,
                student_code=user_code,
                student_chat_history=all_user_messages_str
            )

            async for text in op_ai_wrapper.generate_async_response(
                prompt = model_prompt
            ):
                if text is None:
                    await websocket.send_text('MODEL_GEN_COMPLETE')

                    pg_chat_conversation_object = PlaygroundChatConversation(
                        question = user_question,
                        prompt = model_prompt,
                        response = full_response_message,
                        code = user_code,
                        question_object_id = parent_question_object_id
                        # playground_parent_object_id = parent_pg_object.id
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


## Authenticated

@app.post("/fetch_dashboard_data")
def fetch_dashboard_data(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    authenticated_user_object = get_user_object(
        db = db,
        user_id = None,
        token = token
    )

    question_objects = db.query(UserCreatedPlaygroundQuestion).filter(
        UserCreatedPlaygroundQuestion.custom_user_id == authenticated_user_object.id
    ).order_by(UserCreatedPlaygroundQuestion.created_date.desc()).all()

    rv = []
    count = 1
    for qobject in question_objects:
        number_of_chat_messages = db.query(PlaygroundChatConversation).filter(
            PlaygroundChatConversation.question_object_id == qobject.id
        ).count()

        rv.append({
            'id': qobject.id,
            'count': count,
            'name': qobject.name,
            'number_of_chat_messages': number_of_chat_messages,
            "updated_date": qobject.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            # 'created_date': qobject.created_at.date(),
            # "updated_date": qobject.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
        count += 1

    return {
        'success': True,
        'playground_object_list': rv
    }


@app.post("/fetch_question_data")
def fetch_question_data(
    data: FetchQuestionDetailsSchema,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    authenticated_user_object = get_user_object(
        db = db,
        user_id = None,
        token = token
    )

    question_object_id = data.question_id
    question_object = db.query(UserCreatedPlaygroundQuestion).filter(
        UserCreatedPlaygroundQuestion.id == question_object_id,
        UserCreatedPlaygroundQuestion.custom_user_id == authenticated_user_object.id
    ).first()

    if question_object is None:
        raise HTTPException(status_code=404, detail="Question object not found.")

    current_code = db.query(PlaygroundCode).filter(
        PlaygroundCode.question_object_id == question_object.id
    ).order_by(PlaygroundCode.updated_at.desc()).first()

    if current_code is None:
        current_code_str = ""
    else:
        current_code_str = current_code.code

    final_rv = {
        'question_object_id': question_object_id,
        'name': question_object.name,
        'text': question_object.text,
        'example_io_list':  ast.literal_eval(question_object.example_io_list),
        'current_code': current_code_str
    }

    return {
        'success': True,
        'data': final_rv
    }


@app.post("/fetch_playground_question_chat_messages")
def fetch_playground_question_chat(
    data: FetchQuestionDetailsSchema,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    authenticated_user_object = get_user_object(
        db = db,
        user_id = None,
        token = token
    )

    question_object_id = data.question_id
    question_object = db.query(UserCreatedPlaygroundQuestion).filter(
        UserCreatedPlaygroundQuestion.id == question_object_id,
        UserCreatedPlaygroundQuestion.custom_user_id == authenticated_user_object.id
    ).first()

    if question_object is None:
        raise HTTPException(status_code=404, detail="Question object not found.")

    pg_conversation_objects = db.query(PlaygroundChatConversation).filter(
        PlaygroundChatConversation.question_object_id == question_object.id
    )

    final_rv = []
    for pg_chat_obj in pg_conversation_objects:
        final_rv.append({
            "parent_question_object_id": question_object.id,
            'text':  pg_chat_obj.question,
            'sender': 'user'
        })

        final_rv.append({
            "parent_question_object_id": question_object.id,
            'text':  pg_chat_obj.response,
            'sender': 'ai'
        })
    
    return {
        'success': True,
        'data': final_rv
    }
