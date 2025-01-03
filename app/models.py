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
