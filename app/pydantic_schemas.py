from typing import Optional
from pydantic import BaseModel

class AnonUserSchema(BaseModel):
    user_id: Optional[str] = None
