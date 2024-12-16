from typing import Optional
from pydantic import BaseModel

# class AnonUserSchema(BaseModel):
#     user_id: Optional[str] = None

class RequiredAnonUserSchema(BaseModel):
    user_id: str

class UpdateQuestionSchema(RequiredAnonUserSchema):
    question_id: str
    question_name: str
    question_text: str

class CodeExecutionRequestSchema(BaseModel):
    language: str
    code: str

class SaveCodeSchema(RequiredAnonUserSchema):
    question_id: str
    code: str

class SaveLandingPageEmailSchema(BaseModel):
    email: str
