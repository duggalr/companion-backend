from typing import Optional, Dict, Union, Tuple
import requests
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from app.models import AnonUser, UserOAuth, CustomUser, InitialPlaygroundQuestion
from app.scripts.verify_auth_zero_jwt import verify_jwt


def _check_if_anon_user_exists(anon_user_id: str,db: Session) -> bool:
    anon_user_object = db.query(CustomUser).filter(
        CustomUser.anon_user_id == anon_user_id
    ).first()
    if anon_user_object is None:
        return False
    return True


def create_anon_user_object(anon_user_id: str, db: Session) -> CustomUser:
    if _check_if_anon_user_exists(anon_user_id, db):
        return db.query(CustomUser).filter(
            CustomUser.anon_user_id == anon_user_id
        ).first()
    
    existing_anon_user_object = AnonUser(
        user_unique_id = anon_user_id
    )
    db.add(existing_anon_user_object)
    db.commit()
    db.refresh(existing_anon_user_object)

    anon_custom_user_object = CustomUser(
        anon_user_id = str(anon_user_id)
    )
    db.add(anon_custom_user_object)
    db.commit()
    db.refresh(anon_custom_user_object)
    
    return anon_custom_user_object


def get_anon_custom_user_object(anon_user_id: str, db: Session) -> CustomUser:
    return db.query(CustomUser).filter(
        CustomUser.anon_user_id == anon_user_id
    ).first()


def _get_authenticated_custom_object(token: str, db: Session) -> Tuple[Optional[Dict[str, Union[bool, int, str]]], Optional[CustomUser]]:
    decoded_token_response = verify_jwt(token)
    if 'error' in decoded_token_response:
        raise HTTPException(
            status_code=500, detail="Internal Server Error."
        )

    auth_zero_unique_sub_id = decoded_token_response['sub']

    associated_user_object = db.query(UserOAuth).filter(
        UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
    ).first()
    if associated_user_object is None:
        return None, None
    
    oauth_user_object_unique_id = associated_user_object.auth_zero_unique_sub_id
    custom_user_object = db.query(CustomUser).filter(
        CustomUser.oauth_user_id == oauth_user_object_unique_id
    ).first()

    if custom_user_object is None:
        return None, None

    return None, custom_user_object


def get_user_object(db: Session, user_id: Optional[str], token: Optional[str]):
    if token:
        _, user_object = _get_authenticated_custom_object(token=token, db=db)
        if not user_object:
            raise HTTPException(
                status_code=400,
                detail="Authentication Error."
            )
        return user_object

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID not found."
        )

    return get_anon_custom_user_object(
        user_id = user_id
    )

def _get_random_initial_pg_question(db: Session) -> Optional[InitialPlaygroundQuestion]:
    """
    Fetch a random initial playground question from the database.
    """
    random_initial_question_object = db.query(InitialPlaygroundQuestion).order_by(func.random()).first()
    return random_initial_question_object


async def get_optional_token(request: Request) -> Optional[str]:
    authorization: str = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            return token
    return None