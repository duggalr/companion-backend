import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


## Landing Page ##

class LandingPageEmail(Base):
    """
    Table storing all the emails from the landing page
    """
    __tablename__ = "landing_page_email"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
    created_date = Column(DateTime, server_default=func.now(), nullable=False)


## User Models ##

class AnonUser(Base):
    """
    Anon User Model
    """
    __tablename__ = "anon_user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_unique_id = Column(String, unique=True, index=True, nullable=False)
    created_date = Column(DateTime, server_default=func.now(), nullable=False)

class UserOAuth(Base):
    """
    OAuth User Model
    """
    __tablename__ = "user_oauth"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_zero_unique_sub_id = Column(String, unique=True, index=True, nullable=False)
    given_name = Column(String, index=True, nullable=False)
    family_name = Column(String, index=True, nullable=False)
    full_name = Column(String, index=True, nullable=False)
    profile_picture_url = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified = Column(Boolean, index=True, nullable=False)
    created_date = Column(DateTime, server_default=func.now(), nullable=False)

class CustomUser(Base):
    """
    Custom User Model
    """
    __tablename__ = "custom_user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    anon_user_id = Column(String, ForeignKey('anon_user.user_unique_id'), nullable=True)
    anon_user = relationship("AnonUser")

    oauth_user_id = Column(String, ForeignKey('user_oauth.auth_zero_unique_sub_id'), nullable=True)
    oauth_user = relationship("UserOAuth")

    created_date = Column(DateTime, server_default=func.now(), nullable=False)


## Question Models ##

class QuestionBaseModel(Base):  # Base Model
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)   # TODO: change this to nullable = True (blank question)?
    text = Column(String, nullable=False)   # TODO: change this to nullable = True?
    example_io_list = Column(String, nullable=False)  # TODO: change this to nullable = True?
    created_date = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class InitialPlaygroundQuestion(QuestionBaseModel):
    """
    Constant Table with Initial Questions
    """
    __tablename__ = 'initial_playground_question'

    starter_code = Column(String, nullable=False)
    solution_code = Column(String, nullable=False)
    solution_time_complexity = Column(String, nullable=False)
    test_case_list = Column(String, nullable=True)

class UserCreatedPlaygroundQuestion(QuestionBaseModel):
    __tablename__ = 'user_created_playground_question'

    custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
    custom_user = relationship("CustomUser")


## MIT Course Models

class LectureMain(Base):
    """
    """
    __tablename__ = 'lecture_main'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    number = Column(Integer, nullable=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    # video_url = Column(String, nullable=True)
    notes_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    embed_video_url = Column(String, nullable=True)
    thumbnail_image_url = Column(String, nullable=True)
    code_url = Column(String, nullable=True)

    # lecture_complete = Column(Boolean, default=False)

    created_date = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class UserLectureMain(Base):
    """
    """
    __tablename__ = 'user_lecture_main'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    complete = Column(Boolean, nullable=False, default=False)

    custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
    custom_user = relationship("CustomUser")

    lecture_main_object_id = Column(UUID, ForeignKey('lecture_main.id'))
    lecture_main_object = relationship("LectureMain")


class ProblemSetQuestion(Base):
    """
    """
    __tablename__ = 'problem_set_question'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ps_number = Column(Integer, nullable=False, unique=True)
    ps_name = Column(String, nullable=False)
    ps_url = Column(String, nullable=False, unique=True)

    implementation_in_progress = Column(Boolean, default=False)

    lecture_main_object_id = Column(UUID, ForeignKey('lecture_main.id'))
    lecture_main_object = relationship("LectureMain")

    created_date = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class LectureQuestion(QuestionBaseModel):
    """
    """
    __tablename__ = 'lecture_question'

    starter_code = Column(String, nullable=True)
    correct_solution = Column(String, nullable=True)
    test_case_list = Column(String, nullable=True)
    function_name = Column(String, nullable=True)
    class_name = Column(String, nullable=True)
    test_function_name = Column(String, nullable=True)

    question_type = Column(String, nullable=True)  # TODO: question_type (lecture_exercise or problem_set)
    problem_set_part = Column(String, nullable=True)
    problem_set_number = Column(Integer, ForeignKey('problem_set_question.ps_number'), nullable=True)
    problem_set_object = relationship("ProblemSetQuestion")

    lecture_main_object_id = Column(UUID, ForeignKey('lecture_main.id'))
    lecture_main_object = relationship("LectureMain")


class UserCreatedLectureQuestion(Base):
    """
    """
    __tablename__ = 'user_created_lecture_question'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lecture_question_object_id = Column(UUID, ForeignKey('lecture_question.id'))
    lecture_question = relationship("LectureQuestion")

    complete = Column(Boolean, default=False)

    custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
    custom_user = relationship("CustomUser")

    created_date = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class UserPlaygroundLectureCode(Base):
    """
    """
    __tablename__ = 'user_playground_lecture_code'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    programming_language = Column(String, nullable=False, default='python')
    code = Column(String, nullable=False)
    lecture_question_object_id = Column(UUID, ForeignKey('user_created_lecture_question.id'), nullable=False)
    lecture_question_object =relationship("UserCreatedLectureQuestion")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class LectureCodeSubmissionHistory(Base):
    """
    """
    __tablename__ = "lecture_code_submission_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False)
    test_case_boolean_result = Column(Boolean, default=False)
    program_output_list = Column(String, nullable=False)
    ai_feedback_response_string = Column(String, nullable=False)
    user_created_lecture_question_object_id = Column(UUID, ForeignKey('user_created_lecture_question.id'), nullable=False)
    user_created_lecture_question_object =relationship("UserCreatedLectureQuestion")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)


## Code Models ##

class PlaygroundCode(Base):
    """
    Meant to store the playground code information
    """
    __tablename__ = "playground_code"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    programming_language = Column(String, nullable=False, default='python')
    code = Column(String, nullable=False)
    question_object_id = Column(UUID, ForeignKey('user_created_playground_question.id'), nullable=False)
    parent_question_object = relationship("UserCreatedPlaygroundQuestion")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


## Chat Models ##

class TutorConversationBaseModel(Base):
    """
    Abstract Base Model for covering all Tutor Conversations
    """
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(String, nullable=False)
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class PlaygroundChatConversation(TutorConversationBaseModel):
    """
    Playground Chat Conversation
    """
    __tablename__ = 'playground_chat_conversation'

    code = Column(String, nullable=True)
    question_object_id = Column(UUID, ForeignKey('user_created_playground_question.id'), nullable=False)
    parent_question_object = relationship("UserCreatedPlaygroundQuestion")

class LecturePlaygroundChatConversation(TutorConversationBaseModel):
    """
    """
    __tablename__ = 'lecture_playground_chat_conversation'

    code = Column(String, nullable=True)
    user_lecture_question_object_id = Column(UUID, ForeignKey('user_created_lecture_question.id'), nullable=False)
    user_lecture_question_object = relationship("UserCreatedLectureQuestion")

    # question_object_id = Column(UUID, ForeignKey('user_created_playground_question.id'), nullable=False)
    # parent_question_object = relationship("UserCreatedPlaygroundQuestion")    


# TODO: set ps object id in state
class PlaygroundProblemSetChatConversation(TutorConversationBaseModel):
    """
    """
    __tablename__ = "lecture_playground_problem_set_chat_conversation"

    code = Column(String, nullable=True)
    problem_set_object_id = Column(UUID, ForeignKey('problem_set_question.id'), nullable=False)
    problem_set_object = relationship("ProblemSetQuestion")



## New Course Interface - Related Models

# TODO:
    # start by saving this information for user once created
    # go from there to fetching it and using it during generation of future stuff

class StudentLearnedProfile(Base):
    """
    """
    __tablename__ = 'student_learned_profile'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_summary_text = Column(String)
    user_profile_dict = Column(String)
    user_syllabus_dict = Column(String)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
    custom_user = relationship("CustomUser")


class StudentCourseParent(Base):
    """
    """
    __tablename__ = 'student_course_parent'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    course_name = Column(String)
    course_description = Column(String)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
    custom_user = relationship("CustomUser")


class StudentCourseModule(Base):
    """
    """
    __tablename__ = 'student_course_module'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    module_name = Column(String)
    module_description = Column(String, nullable=True)
    module_sub_list_string = Column(String)

    student_course_parent_object_id = Column(UUID, ForeignKey('student_course_parent.id'), nullable=True)
    student_course_parent_object = relationship("StudentCourseParent")


class StudentCourseSubModule(Base):
    """
    """
    __tablename__ = 'student_course_sub_module'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)    
    
    sub_module_name = Column(String)
    sub_module_list_string = Column(String)

    student_course_module_object_id = Column(UUID, ForeignKey('student_course_module.id'), nullable=True)
    student_course_module_object = relationship('StudentCourseModule')


