import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
# from .database import Base
from app.database import Base


class AnonUser(Base):
    """
    Anon User Model
    """
    __tablename__ = "anon_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_unique_id = Column(String, unique=True, index=True, nullable=False)


class PlaygroundCode(Base):
    """
    Playground Code Model
    """
    __tablename__ = "playground_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False)

    # Foreign key that references AnonUser's user_unique_id
    user_id = Column(String, ForeignKey('anon_users.user_unique_id'), nullable=False)
    # Relationship from PlaygroundCode to AnonUser
    user = relationship("AnonUser")

