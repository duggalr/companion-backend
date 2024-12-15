import os
from typing import Optional, Generator
from celery import Celery
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends

from app.database import SessionLocal
from app.llm import prompts, openai_wrapper
from app.models import AnonUser, CustomUser
from app.pydantic_schemas import RequiredAnonUserSchema
from app.config import settings
from app.utils import create_anon_user_object

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
