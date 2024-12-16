import os
import ast
import json
from json import JSONDecodeError
from typing import Optional, Generator
from celery import Celery
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends

from app.database import SessionLocal
from app.llm import prompts, openai_wrapper
from app.models import InitialPlaygroundQuestion, UserCreatedPlaygroundQuestion
from app.pydantic_schemas import RequiredAnonUserSchema, UpdateQuestionSchema
from app.config import settings
from app.utils import create_anon_user_object, get_anon_custom_user_object, _get_random_initial_pg_question

# TODO: 
    # recreate requirements file and proceed from there
    # get current landing page working
    # **Build V1 of new landing page tonight**

app = FastAPI(
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json"
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


## Views

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


@app.post("/get_random_initial_pg_question")
def get_random_initial_playground_question(
    data: RequiredAnonUserSchema,
    db: Session = Depends(get_db)
):
    # Get Anon User Object
    user_id = data.user_id
    current_custom_user_object = get_anon_custom_user_object(
        anon_user_id = user_id,
        db = db
    )
    if current_custom_user_object is None:
        raise HTTPException(status_code=400, detail="User object not found.")

    # Get Random Question Object
    random_initial_question_object = _get_random_initial_pg_question(
        db = db
    )

    # Create New Question Object
    new_pg_question_object = UserCreatedPlaygroundQuestion(
        name = random_initial_question_object.name,
        text = random_initial_question_object.text,
        example_io_list = random_initial_question_object.example_io_list,
        custom_user_id = current_custom_user_object.id
    )
    db.add(new_pg_question_object)
    db.commit()
    db.refresh(new_pg_question_object)

    to_return = {
        'question_id': new_pg_question_object.id,
        'name': new_pg_question_object.name,
        'text': new_pg_question_object.text,
        'starter_code': random_initial_question_object.starter_code,
        'example_io_list': ast.literal_eval(random_initial_question_object.example_io_list)
    }
    # return response_utils.success_response(data = to_return)
    return {
        'success': True,
        'data': to_return
    }


@app.post("/update_user_question")
def update_user_question(
    data: UpdateQuestionSchema,
    db: Session = Depends(get_db),
    # openai_wrapper: get_openai_wrapper()
    op_ai_wrapper: openai_wrapper.OpenAIWrapper = Depends(get_openai_wrapper)
):
    # Get Anon User Object
    user_id = data.user_id
    current_custom_user_object = get_anon_custom_user_object(
        anon_user_id = user_id,
        db = db
    )
    if current_custom_user_object is None:
        raise HTTPException(status_code=400, detail="User object not found.")

    existing_pg_question_object = db.query(UserCreatedPlaygroundQuestion).filter(
        UserCreatedPlaygroundQuestion.id == data.question_id,
        UserCreatedPlaygroundQuestion.custom_user_id == current_custom_user_object.id 
    ).first()

    if not existing_pg_question_object:
        raise HTTPException(status_code=404, detail="Question object not found or unauthorized.")

    # Generate AI Response
    try:
        prompt = f"{prompts.GENERATE_INPUT_OUTPUT_EXAMPLE_PROMPT}Question: {data.question_text.strip()}\n\n## Output:\n"
        ai_response = op_ai_wrapper.generate_sync_response(
            prompt = prompt
        )
        ai_response_json_dict = json.loads(ai_response.choices[0].message.content)
        example_io_list = ai_response_json_dict["input_output_example_list"]
    except (KeyError, JSONDecodeError):
        raise HTTPException(status_code=500, detail="Invalid AI response format.")


    # Get user object
    custom_user_object = get_user_object()

    # Fetch question
    existing_pg_question_object = db.query(models.UserCreatedPlaygroundQuestion).filter(
        models.UserCreatedPlaygroundQuestion.id == data.question_id,
        models.UserCreatedPlaygroundQuestion.user_id == custom_user_object.id
    ).first()
    if not existing_pg_question_object:
        return not_found_error(
            detail = "Question object not found or Unauthorized."
        )

    # Generate AI Response
    try:
        prompt = f"{prompts.GENERATE_INPUT_OUTPUT_EXAMPLE_PROMPT}Question: {data.question_text.strip()}\n\n## Output:\n"
        ai_response = opai_wrapper.generate_sync_response(prompt=prompt)
        ai_response_json_dict = json.loads(ai_response.choices[0].message.content)
        example_io_list = ai_response_json_dict["input_output_example_list"]
    except (KeyError, JSONDecodeError):
        raise HTTPException(status_code=500, detail="Invalid AI response format.")
