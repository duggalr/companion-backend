from typing import Optional
from pydantic import BaseModel

class NotRequiredAnonUserSchema(BaseModel):
    user_id: Optional[str] = None

class RequiredAnonUserSchema(BaseModel):
    user_id: str

class NotRequiredQuestionIdSchema(BaseModel):
    question_id: Optional[str] = None

class UpdateQuestionSchema(NotRequiredAnonUserSchema, NotRequiredQuestionIdSchema):
    question_name: str
    question_text: str
    example_input_output_list: Optional[list] = None

# class UpdateQuestionSchema(NotRequiredAnonUserSchema):
#     question_id: Optional[str] = None

class ValidateAuthZeroUserSchema(BaseModel):
    email: str
    email_verified: bool
    family_name: str
    full_name: str
    given_name: str
    profile_picture_url: str
    sub_id: str

class CodeExecutionRequestSchema(BaseModel):
    language: str
    code: str

class SaveCodeSchema(UpdateQuestionSchema):
    code: str
    lecture_question: bool

class SaveLandingPageEmailSchema(BaseModel):
    email: str

class FetchQuestionDetailsSchema(BaseModel):
    question_id: str
    lecture_question: Optional[bool] = None

class FetchLessonQuestionDetailSchema(BaseModel):
    lesson_question_id: str

class FetchLectureDetailSchema(BaseModel):
    lecture_number: str
