import os
from typing import Optional, Generator
import ast
from datetime import datetime
import json
from json import JSONDecodeError
import docker
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy import desc
from sqlalchemy.orm import Session

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import SessionLocal
from app.llm import prompts, openai_wrapper
from app.models import UserOAuth, CustomUser, InitialPlaygroundQuestion, UserCreatedPlaygroundQuestion, PlaygroundCode, UserCreatedPlaygroundQuestion, PlaygroundChatConversation, LandingPageEmail, LectureQuestion, UserCreatedLectureQuestion, UserPlaygroundLectureCode, LecturePlaygroundChatConversation, LectureMain, LectureCodeSubmissionHistory, ProblemSetQuestion, PlaygroundProblemSetChatConversation, UserLectureMain
from app.pydantic_schemas import NotRequiredAnonUserSchema, RequiredAnonUserSchema, UpdateQuestionSchema, CodeExecutionRequestSchema, SaveCodeSchema, SaveLandingPageEmailSchema, FetchQuestionDetailsSchema, ValidateAuthZeroUserSchema, FetchLessonQuestionDetailSchema, FetchLectureDetailSchema, LectureQuestionSubmissionSchema, ProblemSetFetchSchema
from app.config import settings
from app.utils import create_anon_user_object, get_anon_custom_user_object, _get_random_initial_pg_question, get_user_object, get_optional_token, clean_question_input_output_list, clean_question_test_case_list
from app.llm.prompt_utils import _prepate_tutor_prompt, _prepare_solution_feedback_prompt
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
    finally:
        db.close()
    # try:
    #     db = SessionLocal()
    #     yield db
    # except Exception as e:
    #     print(f"Database connection error: {e}")
    #     raise HTTPException(status_code=500, detail="Database connection failed")
    # finally:
    #     db.close()

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

    print('CUSTOM AUTH USER:', authenticated_user_object)

    pg_question_object = _get_or_create_user_question_object(
        db = db,
        data = SaveCodeSchema(**{
            'user_id': None,
            'question_id': data.question_id,
            'question_name': data.question_name,
            'question_text': data.question_text,
            'example_input_output_list': data.example_input_output_list,
            'code': '',
            'lecture_question': False
        }),
        custom_user_object = authenticated_user_object
    )

    print('PG QUESTION OBJECT:', pg_question_object)

   # Generate AI Response
    try:
        prompt = f"{prompts.GENERATE_INPUT_OUTPUT_EXAMPLE_PROMPT}Question: {data.question_text.strip()}\n\n## Output:\n"
        ai_response = op_ai_wrapper.generate_sync_response(
            prompt = prompt,
            return_in_json = True
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

    MAX_EXECUTION_TIME_IN_SECONDS = 25

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
    print('DATA - G/C QUESTION:', data)
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
    current_code = data.code
    custom_user_object = get_user_object(
        db,
        data.user_id,
        token
    )
    print('custom-user-object:', custom_user_object)
    print('question_ID:', data.question_id)

    # TODO: need to update here to handle problem set for saving code and other stuff; finish and proceed from there
    if data.lecture_question is True:
        question_object = db.query(UserCreatedLectureQuestion).filter(
            UserCreatedLectureQuestion.id == data.question_id,
            UserCreatedLectureQuestion.custom_user_id == custom_user_object.id
        ).first()
        if question_object is None:
            raise HTTPException(
                status_code=404,
                detail="Question object not found or unauthorized."
            )

        lecture_pg_code_object = UserPlaygroundLectureCode(
            programming_language = 'python',
            code = current_code,
            lecture_question_object_id = question_object.id
        )
        db.add(lecture_pg_code_object)
        db.commit()
        db.refresh(lecture_pg_code_object)
    else:
        question_object = _get_or_create_user_question_object(
            db = db,
            data = data,
            custom_user_object = custom_user_object
        )

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

            print('DATA-WEBSOCKET:', data)

            problem_set_question = data.get('problem_set_question', None)
            problem_set_object_id = data.get('problem_set_object_id', None)

            # TODO: start here

            user_question = data['text'].strip()
            user_code = data['user_code']
            all_user_messages_str = data['all_user_messages_str']
            user_current_problem_name, user_current_problem_text = data['current_problem_name'], data['current_problem_question']

            parent_question_object_id = data['parent_question_object_id']
            is_lecture_question = data['lecture_question']

            print(f"IS LECTURE QUESTION: {is_lecture_question} | {parent_question_object_id}")

            if problem_set_question is True:
                parent_question_object = db.query(ProblemSetQuestion).filter(
                    ProblemSetQuestion.id == problem_set_object_id
                ).first()
                print('PS Object:', parent_question_object)

            elif is_lecture_question is True:
                parent_question_object = db.query(UserCreatedLectureQuestion).filter(
                    UserCreatedLectureQuestion.id == parent_question_object_id
                ).first()

            else:
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
                # Fetch conversation messagess
                if text is None:
                    await websocket.send_text('MODEL_GEN_COMPLETE')
                    
                    # TODO:
                    if problem_set_question:
                        problem_set_chat_conversation_object = PlaygroundProblemSetChatConversation(
                            question = user_question,
                            prompt = model_prompt,
                            response = full_response_message,
                            code = user_code,
                            problem_set_object_id = problem_set_object_id,
                        )
                        db.add(problem_set_chat_conversation_object)
                        db.commit()
                        db.refresh(problem_set_chat_conversation_object)

                    elif is_lecture_question:
                        lecture_chat_conversation_object = LecturePlaygroundChatConversation(
                            question = user_question,
                            prompt = model_prompt,
                            response = full_response_message,
                            user_lecture_question_object_id = parent_question_object.id
                        )
                        db.add(lecture_chat_conversation_object)
                        db.commit()
                        db.refresh(lecture_chat_conversation_object)

                    else:
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


@app.post("/fetch_dashboard_data")
def fetch_dashboard_data(
    data: NotRequiredAnonUserSchema,
    token: Optional[str] = Depends(get_optional_token),
    db: Session = Depends(get_db),
):
    current_custom_user_object = get_user_object(
        db = db,
        user_id = data.user_id,
        token = token
    )
    if current_custom_user_object is None:
        raise HTTPException(status_code=400, detail="User object not found.")


    ## Fetch MIT 6.100 Course Data
    lecture_main_objects = db.query(LectureMain).distinct(LectureMain.number).all()
    lecture_objects_rv = []
    for lm_obj in lecture_main_objects:
        problem_set_question_object = db.query(ProblemSetQuestion).filter(
            ProblemSetQuestion.lecture_main_object_id == lm_obj.id
        ).first()

        lecture_exercise_objects = db.query(LectureQuestion).filter(
            LectureQuestion.lecture_main_object_id == lm_obj.id,
            LectureQuestion.question_type == 'lecture_finger_exercise'
        ).all()

        if len(lecture_exercise_objects) > 0:
            lecture_exercise_list = [
                {'name': lm_exercise_obj.name, 'id': lm_exercise_obj.id, 'complete': False} for lm_exercise_obj in lecture_exercise_objects
            ]
        else:
            lecture_exercise_list = []

        if problem_set_question_object is not None:
            problem_set_dict = {
                'id': problem_set_question_object.id,
                'number': problem_set_question_object.ps_number,
                'name': problem_set_question_object.ps_name,
                'implementation_in_progress': problem_set_question_object.implementation_in_progress,
                'complete': False
            }
        else:
            problem_set_dict = {}

        ## Determine if the exercises have been complete for authenticated user
        current_lecture_main_complete = False
        if token:
            # Lecture Exercises
            for lecture_exercise_di in lecture_exercise_list:
                lec_question_id = lecture_exercise_di['id']
                user_created_lq_object = db.query(UserCreatedLectureQuestion).filter(
                    UserCreatedLectureQuestion.lecture_question_object_id == lec_question_id,
                    UserCreatedLectureQuestion.custom_user_id == current_custom_user_object.id
                ).first()
                if user_created_lq_object is not None:
                    lecture_exercise_di['complete'] = user_created_lq_object.complete
                else:
                    lecture_exercise_di['complete'] = False

            # Problem Set Exercise
            if len(problem_set_dict) > 0:
                problem_set_lec_question_objects = db.query(LectureQuestion).filter(
                    LectureQuestion.problem_set_number == problem_set_question_object.ps_number
                )
                problem_set_complete = True
                for ps_lq_object in problem_set_lec_question_objects:
                    user_created_lq_object = db.query(UserCreatedLectureQuestion).filter(
                        UserCreatedLectureQuestion.lecture_question_object_id == ps_lq_object.id,
                        UserCreatedLectureQuestion.custom_user_id == current_custom_user_object.id
                    ).first()
                    # TODO: why does lecture question get created twice? <-- fix
                    if user_created_lq_object is not None:
                        if not user_created_lq_object.complete:
                            problem_set_complete = False
                            break
                    else:
                        problem_set_complete = False
                        break
  
                problem_set_dict['problem_set_complete'] = problem_set_complete

            user_lecture_main_object = db.query(UserLectureMain).filter(
                UserLectureMain.custom_user_id == current_custom_user_object.id,
                UserLectureMain.complete == True
            ).all()
            if len(user_lecture_main_object) > 0:
                current_lecture_main_complete = True

        lecture_objects_rv.append({
            'id': lm_obj.id,
            'number': lm_obj.number,
            'name': lm_obj.name,
            'description': lm_obj.description,
            'video_url': lm_obj.video_url,
            'notes_url': lm_obj.notes_url,

            # TODO: serious bug --> lecture_complete cannot sit on global lecture-main object <-- fix and proceed from there to ensuring good
            'lecture_completed': current_lecture_main_complete,
            'problem_set_dict': problem_set_dict,
            'lecture_exercise_list': lecture_exercise_list
        })


    ## Fetch User Created Code
    user_created_questions_rv = []
    if token:
        question_objects = db.query(UserCreatedPlaygroundQuestion).filter(
            UserCreatedPlaygroundQuestion.custom_user_id == current_custom_user_object.id
        ).order_by(UserCreatedPlaygroundQuestion.created_date.desc()).all()

        count = 1
        for qobject in question_objects:
            number_of_chat_messages = db.query(PlaygroundChatConversation).filter(
                PlaygroundChatConversation.question_object_id == qobject.id
            ).count()

            user_created_questions_rv.append({
                'id': qobject.id,
                'count': count,
                'name': qobject.name,
                'number_of_chat_messages': number_of_chat_messages,
                "updated_date": qobject.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
            count += 1


    # TODO: render this on the frontend
    return {
        'success': True,
        'lecture_objects_list': lecture_objects_rv,
        'playground_object_list': user_created_questions_rv
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
    print('QUESTION OBJECT ID:', question_object_id)

    try:
        question_object = db.query(UserCreatedPlaygroundQuestion).filter(
            UserCreatedPlaygroundQuestion.id == question_object_id,
            UserCreatedPlaygroundQuestion.custom_user_id == authenticated_user_object.id
        ).first()
    except:
        raise HTTPException(status_code=500, detail="Invalid data")

    if question_object is None:
        raise HTTPException(status_code=404, detail="Item not found")

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
    is_problem_set_question = data.problem_set_question

    print(f"Input Data:", authenticated_user_object, data.lecture_question)

    if is_problem_set_question is True:
        question_object = db.query(ProblemSetQuestion).filter(
            ProblemSetQuestion.id == question_object_id
        ).first()

    elif data.lecture_question is True:
        question_object = db.query(UserCreatedLectureQuestion).filter(
            UserCreatedLectureQuestion.lecture_question_object_id == question_object_id,
            UserCreatedLectureQuestion.custom_user_id == authenticated_user_object.id
        ).first()
        print('QUESTION OBJECT CHAT:', question_object)
    else:
        question_object = db.query(UserCreatedPlaygroundQuestion).filter(
            UserCreatedPlaygroundQuestion.id == question_object_id,
            UserCreatedPlaygroundQuestion.custom_user_id == authenticated_user_object.id
        ).first()

    if question_object is None:
        raise HTTPException(status_code=404, detail="Question object not found.")

    if is_problem_set_question is True:
        pg_conversation_objects = db.query(PlaygroundProblemSetChatConversation).filter(
            PlaygroundProblemSetChatConversation.problem_set_object_id == question_object.id
        ).all()

    elif data.lecture_question is True:
        pg_conversation_objects = db.query(LecturePlaygroundChatConversation).filter(
            LecturePlaygroundChatConversation.user_lecture_question_object_id == question_object.id
        ).all()
    else:
        pg_conversation_objects = db.query(PlaygroundChatConversation).filter(
            PlaygroundChatConversation.question_object_id == question_object.id
        ).all()

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
    
    # TODO: fix this and go from there
    print('final-msg-list:', final_rv)

    return {
        'success': True,
        'data': final_rv
    }


@app.post("/fetch_lecture_data")
def fetch_lecture_data(
    data: FetchLectureDetailSchema,
    # credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    token: Optional[str] = Depends(get_optional_token),
    db: Session = Depends(get_db),
):
    # TODO: pass lecture number and retrieve and display in FE
    lecture_number = data.lecture_number
    print(f"lecture-number: {lecture_number}")

    lm_object = db.query(LectureMain).filter(
        LectureMain.number == lecture_number
    ).first()
    print("LM OBJECT:", lm_object)

    # lecture_associated_exercise_object = db.query(LectureQuestion).filter(
    #     LectureQuestion.lecture_main_object_id == lm_object.id
    # ).first()

    # lecture_associated_exercise_objects = db.query(LectureQuestion).filter(
    #     LectureQuestion.lecture_main_object_id == lm_object.id
    # ).all()
    
    all_associated_lm_objects_for_lec_number = db.query(LectureMain).filter(
        LectureMain.number == lecture_number
    ).all()

    exercise_data_list_rv = []
    for tmp_lm_obj in all_associated_lm_objects_for_lec_number:
        lecture_associated_exercise_object = db.query(LectureQuestion).filter(
            LectureQuestion.lecture_main_object_id == tmp_lm_obj.id
        ).first()
        exercise_data_list_rv.append({
            'id': lecture_associated_exercise_object.id,
            'name': lecture_associated_exercise_object.name,
            # 'question': lecture_associated_exercise_object.text,
            # 'example_io_list': lecture_associated_exercise_object.example_io_list,
            # 'starter_code': lecture_associated_exercise_object.starter_code,
        })


    # fetch problem set for the lecture
    # TODO:
    problem_set_object = db.query(ProblemSetQuestion).filter(
        ProblemSetQuestion.lecture_main_object_id == lm_object.id
    ).first()
    print('Problem Set Object Data:', problem_set_object)
    if problem_set_object is not None:
        problem_set_dict = {}
        problem_set_dict['id'] = problem_set_object.id
        problem_set_dict['ps_number'] = problem_set_object.ps_number
        problem_set_dict['ps_name'] = problem_set_object.ps_name
        problem_set_dict['ps_url'] = problem_set_object.ps_url
        problem_set_dict['implementation_in_progress'] = problem_set_object.implementation_in_progress
    else:
        problem_set_dict = None

    return {
        'success': True,
        'lecture_data': {
            'number': lm_object.number,
            'name': lm_object.name,
            'description': lm_object.description,
            'video_url': lm_object.video_url,
            'embed_video_url': lm_object.embed_video_url,
            'thumbnail_image_url': lm_object.thumbnail_image_url,
            'notes_url': lm_object.notes_url,
            'code_url': lm_object.code_url,
        },
        'exercise_data': exercise_data_list_rv,
        'problem_set_data': problem_set_dict
    }



## MIT OCW Course Related

# TODO: start here and get playground stuff going (first just question rendering and ensuring everything works; then submission)
@app.post("/fetch_lesson_question_data")
def fetch_lesson_question_data(
    data: FetchLessonQuestionDetailSchema,
    token: Optional[str] = Depends(get_optional_token),
    # credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    lesson_qid = data.lesson_question_id
    print('lesson_qid:', lesson_qid)

    authenticated_user_object = None
    if (token):
        # token = credentials.credentials
        authenticated_user_object = get_user_object(
            db = db,
            user_id = None,
            token = token
        )

    # print('authenticated_user_object:', authenticated_user_object, authenticated_user_object.id)

    lecture_question_object = db.query(LectureQuestion).filter(
        LectureQuestion.id == lesson_qid
    ).first()
    print('lecture-QOBJECT:', lecture_question_object)

    if authenticated_user_object is not None:

        num_user_created_lecture_q_objects = db.query(UserCreatedLectureQuestion).filter(
            UserCreatedLectureQuestion.lecture_question_object_id == lecture_question_object.id,
            UserCreatedLectureQuestion.custom_user_id == authenticated_user_object.id
        ).count()

        print('num_user_created_lecture_q_objects-new:', num_user_created_lecture_q_objects)

        current_code_object = None
        if num_user_created_lecture_q_objects > 0:
            user_l_question_obj = db.query(UserCreatedLectureQuestion).filter(
                UserCreatedLectureQuestion.lecture_question_object_id == lecture_question_object.id,
                UserCreatedLectureQuestion.custom_user_id == authenticated_user_object.id
            ).first()

            print('user_l_question_obj:', user_l_question_obj.id)

            current_code_object = db.query(UserPlaygroundLectureCode).filter(
                UserPlaygroundLectureCode.lecture_question_object_id == user_l_question_obj.id
            ).order_by(UserPlaygroundLectureCode.created_at.desc()).first()

            print('current-code-object:', current_code_object)

        else:
            user_l_question_obj = UserCreatedLectureQuestion(
                lecture_question_object_id = lecture_question_object.id,
                custom_user_id = authenticated_user_object.id
            )
            db.add(user_l_question_obj)
            db.commit()
            db.refresh(user_l_question_obj)

        print('USER LS Q OBJECT AND CODE:', user_l_question_obj, current_code_object)

    else:
        current_code_object = None

    ## Fetching test cases list
    test_case_list_literal = ast.literal_eval(lecture_question_object.test_case_list)
    print('test_case_list_literal:', test_case_list_literal)

    test_case_rv_list = []
    for di in test_case_list_literal:
        print('tmp-di:', di)
        input_values_dict = di['input']
        input_values_str = ""
        for inp_k in input_values_dict:
            input_values_str += f"{inp_k} = {input_values_dict[inp_k]}, "
        
        print(input_values_str)
        test_case_rv_list.append({
            'input': input_values_str.strip()[:-1],
            'output': di['expected_output']
        })

        # input_tc_list = ", ".join([[k, di['input'][k]] for k in di['input']])
        # print('inp', input_tc_list)
        # # test_case_rv_list.append()

    print('tc-result-list-rv:', test_case_rv_list)

    user_code_submission_history_objects = []
    user_code_submission_history_object_rv = []
    if authenticated_user_object is not None:
        # user_code_submission_history_objects = db.query(LectureCodeSubmissionHistory).filter(
        #     LectureCodeSubmissionHistory.user_created_lecture_question_object_id == user_l_question_obj.id
        # ).all()
        user_code_submission_history_objects = (
            db.query(LectureCodeSubmissionHistory)
            .filter(
                LectureCodeSubmissionHistory.user_created_lecture_question_object_id
                == user_l_question_obj.id
            )
            .order_by(desc(LectureCodeSubmissionHistory.created_at))  # Replace `created_at` with your desired column
            .all()
        )

        for sub_hist_obj in user_code_submission_history_objects:
            user_code_submission_history_object_rv.append({
                'lc_submission_history_object_id': sub_hist_obj.id,
                'lc_submission_history_object_boolean_result': sub_hist_obj.test_case_boolean_result,
                'lc_submission_history_code': sub_hist_obj.code,
                'lc_submission_history_object_created': sub_hist_obj.created_at,

                'ai_tutor_submission_feedback': sub_hist_obj.ai_feedback_response_string
            })

    rv_dict = {}
    lecture_main_object = db.query(LectureMain).filter(
        LectureMain.id == lecture_question_object.lecture_main_object_id
    ).first()
    rv_dict['next_lecture_number'] = lecture_main_object.number

    if authenticated_user_object is not None:
        rv_dict['question_object_id'] = str(user_l_question_obj.id)
    else:
        rv_dict['question_object_id'] = str(lecture_question_object.id)


    # ## TODO: order-by all questions retrieval
    # ## next question
    # all_questions_for_current_lecture_objects = db.query(LectureQuestion).filter(
    #     LectureQuestion.lecture_main_object_id == lecture_main_object.id
    # ).all()

    next_q = True
    all_lm_objects = db.query(LectureMain).filter(
        LectureMain.number == lecture_main_object.number
    ).all()
    for lm_obj in all_lm_objects:
        current_question_for_lm_object = db.query(LectureQuestion).filter(
            LectureQuestion.lecture_main_object_id == lm_obj.id,
            LectureQuestion.created_date > lecture_question_object.created_date
        ).first()
        if current_question_for_lm_object is not None:
            if current_question_for_lm_object.id != lecture_question_object.id:
                rv_dict['next_question_object_type'] = current_question_for_lm_object.question_type
                
                # TODO: abstract this
                if current_question_for_lm_object.question_type == 'problem_set':
                    rv_dict['next_question_object_id'] = db.query(ProblemSetQuestion).filter(ProblemSetQuestion.lecture_main_object_id == lm_obj.id).first().id
                else:
                    rv_dict['next_question_object_id'] = current_question_for_lm_object.id
                    
                next_q = False
                break

    # if len(all_questions_for_current_lecture_objects) > 1:
    #     last_question = all_questions_for_current_lecture_objects[len(all_questions_for_current_lecture_objects)-1]
    #     if last_question.id != lecture_question_object.id:
    #         rv_dict['next_question_object_id'] = last_question.id

    if next_q is True:
        next_lecture_main_object = db.query(LectureMain).filter(
            LectureMain.number == (lecture_main_object.number + 1)
        ).first()
        print("next_lecture_main_object:", next_lecture_main_object)
        if (next_lecture_main_object is None):
            rv_dict['next_question_object_id'] = None
            rv_dict['next_question_object_type'] = None
        else:
            next_lecture_qst_object = db.query(LectureQuestion).filter(
                LectureQuestion.lecture_main_object_id == next_lecture_main_object.id
            ).first()
            rv_dict['next_question_object_type'] = next_lecture_qst_object.question_type

            if next_lecture_qst_object.question_type == 'problem_set':
                rv_dict['next_question_object_id'] = db.query(ProblemSetQuestion).filter(ProblemSetQuestion.lecture_main_object_id == next_lecture_main_object.id).first().id
            else:
                rv_dict['next_question_object_id'] = next_lecture_qst_object.id

            # rv_dict['next_question_object_id'] = next_lecture_qst_object.id


    cleaned_io_list = clean_question_input_output_list(
        input_output_list = ast.literal_eval(lecture_question_object.example_io_list)
    )
    cleaned_tc_list = clean_question_test_case_list(
        test_case_list = ast.literal_eval(lecture_question_object.test_case_list)
    )

    rv_dict.update({
        'name': lecture_question_object.name,
        'exercise': lecture_question_object.text,
        
        # 'input_output_list': ast.literal_eval(lecture_question_object.example_io_list),
        'input_output_list': cleaned_io_list,

        'user_code': lecture_question_object.starter_code if current_code_object is None else current_code_object.code,
        
        # 'test_case_list': test_case_rv_list,
        'test_case_list': cleaned_tc_list,

        'user_code_submission_history_objects': user_code_submission_history_object_rv
    })

    return {
        'success': True,
        'data': rv_dict,
        # 'user_question_lecture_object_id': user_l_question_obj.id
    }


# from app.scripts.handle_test_case_submission import run_test_cases
from app.code_execution_utils import run_test_cases_without_function, run_test_cases_with_function, run_test_cases_with_class

@app.post("/handle_lecture_question_submission")
def handle_lecture_question_submission(
    data: LectureQuestionSubmissionSchema,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    op_ai_wrapper: openai_wrapper.OpenAIWrapper = Depends(get_openai_wrapper)
):
    user_created_question_id = data.lecture_question_id
    print('lesson_qid:', user_created_question_id)

    token = credentials.credentials
    authenticated_user_object = get_user_object(
        db = db,
        user_id = None,
        token = token
    )
    print('authenticated_user_object:', authenticated_user_object, authenticated_user_object.id)

    user_created_lecture_question_object = db.query(UserCreatedLectureQuestion).filter(
        UserCreatedLectureQuestion.id == user_created_question_id
    ).first()
    print('user_created_lecture_question_object-new:', user_created_lecture_question_object)

    parent_lecture_question_object = db.query(LectureQuestion).filter(
        LectureQuestion.id == user_created_lecture_question_object.lecture_question_object_id
    ).first()
    print('parent-lecture-QOBJECT:', parent_lecture_question_object)

    user_code = data.code
    print(f"User CODE:\n{user_code}")

    # lecture_question_object.test_case_list
    question_literal_tc_list = ast.literal_eval(parent_lecture_question_object.test_case_list)
    tc_return_list = []
    for tc_di in question_literal_tc_list:
        input_tc_dict = tc_di['input']
        tc_return_list.append({
            'input': input_tc_dict,
            "expected_output": tc_di["expected_output"]
        })

    tc_function_name = parent_lecture_question_object.test_function_name

    tc_results = None
    if tc_function_name == 'run_test_cases_without_function':
        tc_results = run_test_cases_without_function(
            user_code = user_code,
            test_case_list = ast.literal_eval(parent_lecture_question_object.test_case_list)
        )

    elif tc_function_name == 'run_test_cases_with_function':
        tc_results = run_test_cases_with_function(
            user_code = user_code,
            function_name = parent_lecture_question_object.function_name,
            test_case_list = ast.literal_eval(parent_lecture_question_object.test_case_list)
        )
    
    elif tc_function_name == 'run_test_cases_with_class':
        # TODO: 
        run_test_cases_with_class(
            user_code = user_code,
            class_name = parent_lecture_question_object.class_name,
            test_case_list = ast.literal_eval(parent_lecture_question_object.test_case_list)
        )

    # tc_results = globals()[tc_function_name]()
    print("Results:", tc_results)

    all_tests_passed = True
    for rslt in tc_results:
        if rslt['correct'] != 'yes':
            all_tests_passed = False
            break

    serialized_test_case_results = json.dumps(tc_results, indent=2)
    solution_fb_prompt = _prepare_solution_feedback_prompt(
        user_code = user_code,
        correct_solution = parent_lecture_question_object.correct_solution,
        test_case_result_boolean = all_tests_passed,
        test_case_result_list_str = serialized_test_case_results
    )
    print(solution_fb_prompt)

    tc_results_output_list = []
    for eval_dict in tc_results:
        program_output = str(eval_dict['program_output'])
        expected_output = str(eval_dict['expected_output'])
        eval_dict['program_output'] = program_output
        eval_dict['expected_output'] = expected_output
        tc_results_output_list.append(eval_dict)

    print('tc_results_output_list-NEW-NEW:', tc_results_output_list)

    # TODO: uncomment the ai_response
    ai_response = op_ai_wrapper.generate_sync_response(
        prompt = solution_fb_prompt,
        return_in_json = False
    )
    ai_response_string = ai_response.choices[0].message.content
    print('AI Response String:', ai_response_string)

    # ai_response_string = "testing..."

    lc_submission_history_object = LectureCodeSubmissionHistory(
        code = user_code,
        test_case_boolean_result = all_tests_passed,
        program_output_list = str(tc_results),
        ai_feedback_response_string = ai_response_string,
        user_created_lecture_question_object_id = user_created_lecture_question_object.id
    )
    db.add(lc_submission_history_object)
    db.commit()
    db.refresh(lc_submission_history_object)

    # TODO: update the following
        # if test-case-passed --> mark current question as complete
        # fetch all questions for this lecture --> count number of complete
            # if complete-count == total_count --> mark as completed

    # if true --> update
    if all_tests_passed:

        print('Updating lecture question as passed')
        user_created_lecture_question_object.complete = True
        db.add(user_created_lecture_question_object)
        db.commit()
        db.refresh(user_created_lecture_question_object)

        parent_lm_object = db.query(LectureMain).filter(
            LectureMain.id == parent_lecture_question_object.lecture_main_object_id
        ).first()
        # fetch all lm objects with lec-number
        all_current_lm_objects = db.query(LectureMain).filter(
            LectureMain.number == parent_lm_object.number
        ).all()

        # fetch lecture questions for lm object
        total_questions_passed = 0
        total_questions_count = len(all_current_lm_objects)
        for current_lm_obj in all_current_lm_objects:
            tmp_lq_object = db.query(LectureQuestion).filter(
                LectureQuestion.lecture_main_object_id == current_lm_obj.id
            ).first()

            user_created_q_for_lq_objects = db.query(UserCreatedLectureQuestion).filter(
                UserCreatedLectureQuestion.lecture_question_object_id == tmp_lq_object.id
            ).all()

            for user_created_q_obj in user_created_q_for_lq_objects:
                if user_created_q_obj.complete is True:
                    total_questions_passed += 1
                # success_code_submission_count_for_lq = db.query(LectureCodeSubmissionHistory).filter(
                #     LectureCodeSubmissionHistory.user_created_lecture_question_object_id == user_created_q_obj.id,
                #     (LectureCodeSubmissionHistory.test_case_boolean_result) == True
                # ).count()
                # # print(f'success-submissions-count for lect-number {lm_obj.number} is {success_code_submission_count_for_lq}')
                # if success_code_submission_count_for_lq > 0:
                #     # question_passed = True
                #     total_questions_passed += 1

        print(f"Total: {total_questions_count} | Total Passed: {total_questions_passed} | Lecture: {parent_lm_object.number}")

        current_lecture_completed = False
        if (total_questions_count == total_questions_passed):
            current_lecture_completed = True

        # TODO:
        print('Creating or Update User Lecture Main Object...')
        existing_user_lecture_main_obj = db.query(UserLectureMain).filter(
            UserLectureMain.lecture_main_object_id == parent_lecture_question_object.lecture_main_object_id
        ).first()
        if existing_user_lecture_main_obj is not None:
            existing_user_lecture_main_obj.complete = current_lecture_completed
            db.add(existing_user_lecture_main_obj)
            db.commit()
            db.refresh(existing_user_lecture_main_obj)
        else:
            user_lec_main_object = UserLectureMain(
                complete = current_lecture_completed,
                custom_user_id = authenticated_user_object.id,
                lecture_main_object_id = parent_lecture_question_object.lecture_main_object_id,
            )
            db.add(user_lec_main_object)
            db.commit()
            db.refresh(user_lec_main_object)

        # parent_lm_object.lecture_complete = current_lecture_completed
        # db.add(parent_lm_object)
        # db.commit()
        # db.refresh(parent_lm_object)

        ## TODO: Create new user-lecture and add True
        # Fine to just create another one upon each submission as it doesn't do any harm <-- although ideal would be 1-to-1 mapping

    return {
        'success': True,
        'data': {
            'lc_submission_history_object_id': lc_submission_history_object.id,
            'lc_submission_history_object_created': lc_submission_history_object.created_at,
            'lc_submission_history_object_boolean_result': lc_submission_history_object.test_case_boolean_result,
            'lc_submission_history_code': lc_submission_history_object.code,

            # 'result_list': tc_results,
            'result_list': tc_results_output_list,
            'all_tests_passed': all_tests_passed,
            'ai_response': ai_response_string
        }
    }


@app.post("/fetch_course_progress")
def fetch_course_progress(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    completed_lecture_objects = db.query(LectureMain).filter(
        LectureMain.lecture_complete == True
    ).count()

    total_lecture_objects = db.query(LectureMain).count()
    percent_complete = round((completed_lecture_objects / total_lecture_objects) * 100, 0)

    return {
        'success': True,
        'percent_complete': percent_complete,
        'completed': completed_lecture_objects,
        'total': total_lecture_objects,
        'remaining': (total_lecture_objects - completed_lecture_objects)
    }


@app.post("/fetch_problem_set_question_data")
def fetch_problem_set_question_data(
    data: ProblemSetFetchSchema,
    token: Optional[str] = Depends(get_optional_token),
    db: Session = Depends(get_db)
):
    authenticated_user_object = None
    if (token):
        # token = credentials.credentials
        authenticated_user_object = get_user_object(
            db = db,
            user_id = None,
            token = token
        )

    ps_object_id = data.problem_set_object_id
    ps_question_object = db.query(ProblemSetQuestion).filter(
        ProblemSetQuestion.id == ps_object_id
    ).first()

    if ps_question_object is None:
        raise HTTPException(status_code=404, detail="Problem Set Not Found.")

    problem_set_lec_question_objects = db.query(LectureQuestion).filter(
        LectureQuestion.problem_set_number == ps_question_object.ps_number
    ).all()

    ## TODO: Fetching next question
    lecture_main_object = db.query(LectureMain).filter(
        LectureMain.id == problem_set_lec_question_objects[0].lecture_main_object_id
    ).first()

    next_lecture_main_object = db.query(LectureMain).filter(
        LectureMain.number == (lecture_main_object.number + 1)
    ).first()
    print("next_lecture_main_object:", next_lecture_main_object)

    if (next_lecture_main_object is None):
        # rv_dict['next_question_object_id'] = None
        next_question_object_id = None
        next_question_object_type = None
    else:
        next_lecture_qst_object = db.query(LectureQuestion).filter(
            LectureQuestion.lecture_main_object_id == next_lecture_main_object.id
        ).first()
        if next_lecture_qst_object is not None:
            next_question_object_id = next_lecture_qst_object.id
            next_question_object_type = next_lecture_qst_object.question_type
            if next_question_object_type == 'problem_set':
                next_question_object_id = db.query(ProblemSetQuestion).filter(ProblemSetQuestion.lecture_main_object_id == next_lecture_main_object.id).first().id
        else:  # TODO: verify here
            next_question_object_id = None
            next_question_object_type = None

    ## Preparing Return Dictionary
    final_return_dict = {}
    user_created_lecture_question_list = []
    for idx, lec_q_object in enumerate(problem_set_lec_question_objects):

        # print("INPUT OUTPUT LITERAL:", ast.literal_eval(lec_q_object.example_io_list))

        cleaned_io_list = clean_question_input_output_list(
            input_output_list = ast.literal_eval(lec_q_object.example_io_list)
        )
        cleaned_tc_list = clean_question_test_case_list(
            test_case_list = ast.literal_eval(lec_q_object.test_case_list)
        )

        tmp_dict = {
            "name": lec_q_object.name,
            "question": lec_q_object.text,
            # "input_output_list": ast.literal_eval(lec_q_object.example_io_list),
            "input_output_list": cleaned_io_list,
            "code": lec_q_object.starter_code,

            "lecture_question": True,
            # "test_case_list": ast.literal_eval(lec_q_object.test_case_list),
            "test_case_list": cleaned_tc_list,

            "next_lecture_number": lecture_main_object.number,
            "next_question_object_id": None,

            "problem_set_question": True,
            "problem_set_current_part": idx,
            "problem_set_next_part": idx + 1,
            "problem_set_number": lec_q_object.problem_set_number
        }

        ## Fetching test cases list for specific question
        test_case_list_literal = ast.literal_eval(lec_q_object.test_case_list)
        # print('test_case_list_literal:', test_case_list_literal)

        test_case_rv_list = []
        for di in test_case_list_literal:
            input_values_dict = di['input']
            input_values_str = ""
            for inp_k in input_values_dict:
                input_values_str += f"{inp_k} = {input_values_dict[inp_k]}, "

            output_value = di['expected_output']
            
            output_values_str = ""
            if isinstance(output_value, dict):
                # for out_k in output_value:
                #     output_values_str += f"{out_k} = {output_value[out_k]}, "
                # output_values_str = output_values_str.strip()[:-1]
                output_values_str = str(output_value)
            else:
                output_values_str = output_value

            print("OUTPUT VALUE STRING NEW:", output_values_str)
            test_case_rv_list.append({
                'input': input_values_str.strip()[:-1],
                'output': output_values_str
            })

        # tmp_dict['test_case_list'] = test_case_rv_list

        if idx == (len(problem_set_lec_question_objects)-1):
            # tmp_dict['next_lecture_number'] = lecture_main_object.number
            tmp_dict['next_question_object_id'] = next_question_object_id
            tmp_dict['next_question_object_type'] = next_question_object_type
            tmp_dict['problem_set_next_part'] = None

        user_created_lec_q_object = None
        if authenticated_user_object is not None:
            user_created_lec_q_object = db.query(UserCreatedLectureQuestion).filter(
                UserCreatedLectureQuestion.lecture_question_object_id == lec_q_object.id,
                UserCreatedLectureQuestion.custom_user_id == authenticated_user_object.id
            ).first()
            
            if user_created_lec_q_object is None:
                user_created_lec_q_object = UserCreatedLectureQuestion(
                    lecture_question_object_id = lec_q_object.id,
                    custom_user_id = authenticated_user_object.id
                )
                db.add(user_created_lec_q_object)
                db.commit()
                db.refresh(user_created_lec_q_object)

            user_created_lecture_question_list.append(str(user_created_lec_q_object.id))
            
            # else:
            #     current_lec_q_code_object_list = db.query(UserPlaygroundLectureCode).filter(
            #         UserPlaygroundLectureCode.lecture_question_object_id == user_created_lec_q_object.id
            #     ).order_by(UserPlaygroundLectureCode.created_at.desc()).all()
            #     # TODO: 
            #     if len(current_lec_q_code_object_list) > 0:
            #         tmp_dict["code"] = current_lec_q_code_object_list[0].code

            tmp_dict["question_id"] = user_created_lec_q_object.id
        else:
            tmp_dict["question_id"] = lec_q_object.id


        ## Fetching Submission History
        user_code_submission_history_objects = []
        user_code_submission_history_object_rv = []
        if authenticated_user_object is not None:
            # user_code_submission_history_objects = db.query(LectureCodeSubmissionHistory).filter(
            #     LectureCodeSubmissionHistory.user_created_lecture_question_object_id == user_l_question_obj.id
            # ).all()

            user_code_submission_history_objects = (
                db.query(LectureCodeSubmissionHistory)
                .filter(
                    LectureCodeSubmissionHistory.user_created_lecture_question_object_id
                    == user_created_lec_q_object.id
                )
                .order_by(desc(LectureCodeSubmissionHistory.created_at))  # Replace `created_at` with your desired column
                .all()
            )

            for sub_hist_obj in user_code_submission_history_objects:
                user_code_submission_history_object_rv.append({
                    'lc_submission_history_object_id': sub_hist_obj.id,
                    'lc_submission_history_object_boolean_result': sub_hist_obj.test_case_boolean_result,
                    'lc_submission_history_code': sub_hist_obj.code,
                    'lc_submission_history_object_created': sub_hist_obj.created_at,

                    'ai_tutor_submission_feedback': sub_hist_obj.ai_feedback_response_string
                })
    
        tmp_dict["user_code_submission_history_objects"] = user_code_submission_history_object_rv

        final_return_dict[idx] = tmp_dict


    print("user_created_lecture_question_list:", user_created_lecture_question_list)

    current_lec_q_code_object_list = db.query(UserPlaygroundLectureCode).filter(
        UserPlaygroundLectureCode.lecture_question_object_id.in_(tuple(user_created_lecture_question_list))
    ).order_by(UserPlaygroundLectureCode.created_at.desc()).all()

    print('current_lec_q_code_object_list-new:', current_lec_q_code_object_list)
    if len(current_lec_q_code_object_list) > 0:
        current_code_string = current_lec_q_code_object_list[0].code
        for idx in final_return_dict:
            final_return_dict[idx]['code'] = current_code_string

    return {
        'success': True,
        'data': final_return_dict,
        'current_question_state': final_return_dict[0]
    }

    # lecture_main_object = db.query(LectureMain).filter(
    #     LectureMain.id == problem_set_question_objects[0].lecture_main_object_id
    # ).first()

    # next_lecture_main_object = db.query(LectureMain).filter(
    #     LectureMain.number == (lecture_main_object.number + 1)
    # ).first()
    # print("next_lecture_main_object:", next_lecture_main_object)

    # if (next_lecture_main_object is None):
    #     # rv_dict['next_question_object_id'] = None
    #     next_question_object_id = None
    # else:
    #     next_lecture_qst_object = db.query(LectureQuestion).filter(
    #         LectureQuestion.lecture_main_object_id == next_lecture_main_object.id
    #     ).first()
    #     next_question_object_id = next_lecture_qst_object.id

    # rv = {}
    # for idx, ps_obj in enumerate(problem_set_question_objects):
    #     tmp_dict = {
    #         "question_id": ps_obj.id,
    #         "name": ps_obj.name,
    #         "question": ps_obj.text,
    #         "input_output_list": ast.literal_eval(ps_obj.example_io_list),
    #         "code": ps_obj.starter_code,

    #         "lecture_quesiton": True,
    #         "test_case_list": ast.literal_eval(ps_obj.test_case_list),

    #         "next_lecture_number": None,
    #         "next_question_object_id": None,

    #         "problem_set_question": True,
    #         # "problem_set_current_part": ps_obj.problem_set_part,
    #         'problem_set_current_part': idx,
    #         'problem_set_next_part': idx + 1,
    #         "problem_set_number": ps_obj.problem_set_number
    #     }

    #     if idx == (len(problem_set_question_objects)-1):
    #         tmp_dict['next_lecture_number'] = lecture_main_object.number
    #         tmp_dict['next_question_object_id'] = next_question_object_id
    #         tmp_dict['problem_set_next_part'] = None

    #     rv[idx] = tmp_dict

    # return {
    #     'success': True,
    #     'data': rv,
    #     'current_question_state': rv[0]
    # }



            # tmp_dict = {
            #     "question_id": user_created_lec_q_object.id,
            #     "name": lec_q_object.name,
            #     "question": lec_q_object.text,
            #     "input_output_list": ast.literal_eval(lec_q_object.example_io_list),
            #     "code": lec_q_object.starter_code,

            #     "lecture_question": True,
            #     "test_case_list": ast.literal_eval(lec_q_object.test_case_list),

            #     "next_lecture_number": None,
            #     "next_question_object_id": None,

            #     "problem_set_question": True,
            #     # "problem_set_current_part": ps_obj.problem_set_part,
            #     'problem_set_current_part': idx,
            #     'problem_set_next_part': idx + 1,
            #     "problem_set_number": lec_q_object.problem_set_number
            # }
