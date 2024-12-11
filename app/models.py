import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


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


## Question Models
class QuestionBaseModel(Base):  # Base Model
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    text = Column(String, nullable=False)
    example_io_list = Column(String, nullable=False)
    created_date = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

# constant table that isn't to be manipulated
class InitialPlaygroundQuestion(QuestionBaseModel):
    __tablename__ = 'initial_playground_question'

    starter_code = Column(String, nullable=False)
    solution_code = Column(String, nullable=False)
    solution_time_complexity = Column(String, nullable=False)
    test_case_list = Column(String, nullable=True)

class UserCreatedPlaygroundQuestion(QuestionBaseModel):
    __tablename__ = 'user_created_playground_question'

    custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
    custom_user = relationship("CustomUser")


## Code Models
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


## Chat Models

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





## OLD Tutor Models 

# class GeneralTutorParentObject(Base):
#     """
#     General Tutor Parent Object
#     """
#     __tablename__ = 'general_tutor_parent_object'

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     unique_name = Column(String, nullable=True)  # in anon case, this will be empty

#     created_at = Column(DateTime, server_default=func.now(), nullable=False)
#     updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

#     custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
#     custom_user = relationship("CustomUser")


# class GeneralTutorChatConversation(Base):
#     """
#     General Tutor Chat Conversation
#     """
#     __tablename__ = 'general_tutor_chat_conversation'

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_message = Column(String, nullable=False)
#     prompt = Column(String, nullable=False)
#     model_response = Column(String, nullable=False)
#     created_date = Column(DateTime, server_default=func.now(), nullable=False)

#     general_tutor_parent_object_id = Column(UUID, ForeignKey("general_tutor_parent_object.id"), nullable=True)
#     general_tutor_parent_object = relationship("GeneralTutorParentObject")


## OLD Playground Models

# class PlaygroundObjectBase(Base):
#     """
#     Base model for Playground Code Data
#     """
#     __tablename__ = "playground_object"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     unique_name = Column(String, nullable=True)
#     created_at = Column(DateTime, server_default=func.now(), nullable=False)
#     updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

#     custom_user_id = Column(UUID, ForeignKey('custom_user.id'), nullable=True)
#     custom_user = relationship("CustomUser")


# class PlaygroundCode(Base):
#     """
#     Meant to store the playground code information
#     """
#     __tablename__ = "playground_code"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     programming_language = Column(String, nullable=False, default='python')
#     code = Column(String, nullable=False)
#     created_date = Column(DateTime, server_default=func.now(), nullable=False)
#     playground_parent_object_id = Column(UUID, ForeignKey("playground_object.id"), nullable=True)
#     playground_parent_object = relationship("PlaygroundObjectBase")


# class PlaygroundCodeRun(Base):
#     """
#     Playground Code Run Model
#         -- tracks runs from the playground code editor
#     """
#     __tablename__ = "playground_code_run"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     created_date = Column(DateTime, server_default=func.now(), nullable=False)
#     playground_parent_object_id = Column(UUID, ForeignKey("playground_object.id"), nullable=True)
#     playground_parent_object = relationship("PlaygroundObjectBase")


# class PlaygroundChatConversation(Base):
#     """
#     Playground Chat Conversation
#     """
#     __tablename__ = 'playground_chat_conversation'

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     question = Column(String, nullable=False)
#     prompt = Column(String, nullable=False)
#     response = Column(String, nullable=False)
#     code = Column(String, nullable=True)

#     playground_parent_object_id = Column(UUID, ForeignKey("playground_object.id"), nullable=True)
#     playground_parent_object = relationship("PlaygroundObjectBase")

#     created_date = Column(DateTime, server_default=func.now(), nullable=False)










# class PlaygroundQuestion(Base):
#     """
#     Playground Question
#     """
#     __tablename__ = 'playground_question'

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String, nullable=False)
#     text = Column(String, nullable=False)
#     starter_code = Column(String, nullable=True)
#     solution_code = Column(String, nullable=True)
#     solution_time_complexity = Column(String, nullable=True)
#     example_io_list = Column(String, nullable=False)
#     test_case_list = Column(String, nullable=True)
#     created_date = Column(DateTime, server_default=func.now(), nullable=False)


# # class Submission(Base):
# #     """
# #     """
