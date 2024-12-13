from typing import Optional, Tuple, Union, Dict
import requests
from fastapi import Request, HTTPException
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import Session
from app import models


def get_random_initial_playground_question(db: Session) -> Optional[models.InitialPlaygroundQuestion]:
    """
    Fetch a random initial playground question from the database.
    """
    random_initial_question_object = db.query(models.InitialPlaygroundQuestion).order_by(func.random()).first()
    return random_initial_question_object


def _get_anon_user_information(user_id: str, db: Session) -> Optional[models.CustomUser]:
    """
    """
    anon_custom_user_object = db.query(models.CustomUser).filter(
        models.CustomUser.anon_user_id == user_id
    ).first()
    return anon_custom_user_object


def _get_auth_zero_user_info(token: str) -> Dict[str, Union[bool, int, str]]:
    """
    """
    url = f"https://dev-2qo458j0ehopg3ae.us.auth0.com/userinfo"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        final_rv = {
            "success": False,
            "status_code": response.status_code,
            "message": response.text
        }
        return final_rv
    else:
        final_rv = {
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        }


def _get_authenticated_custom_object(token: str, db: Session) -> Tuple[Optional[Dict[str, Union[bool, int, str]]], Optional[models.CustomUser]]:
    response = _get_auth_zero_user_info(token)
    if response['success'] is False:
        return response, None
    else:
        user_information_dict = response['data']
        auth_zero_unique_sub_id = user_information_dict['sub']

        associated_user_object = db.query(models.UserOAuth).filter(
            models.UserOAuth.auth_zero_unique_sub_id == auth_zero_unique_sub_id
        ).first()
        if associated_user_object is None:
            return None, None
        
        oauth_user_object_unique_id = associated_user_object.auth_zero_unique_sub_id
        custom_user_object = db.query(models.CustomUser).filter(
            models.CustomUser.oauth_user_id == oauth_user_object_unique_id
        ).first()

        if custom_user_object is None:
            return None, None

        return None, custom_user_object


def get_user_object(db: Session, user_id: Optional[str], token: Optional[str]):
    if token:
        _, user_object = _get_authenticated_custom_object(token=token, db=db)
        if not user_object:
            # return response_utils.bad_request_error(
            #     data = {},
            #     detail = "Authentication Error."
            # )
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

    return _get_anon_user_information(user_id=user_id)
