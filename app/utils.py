from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from app.models import AnonUser, CustomUser, InitialPlaygroundQuestion


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

def _get_random_initial_pg_question(db: Session) -> Optional[InitialPlaygroundQuestion]:
    """
    Fetch a random initial playground question from the database.
    """
    random_initial_question_object = db.query(InitialPlaygroundQuestion).order_by(func.random()).first()
    return random_initial_question_object
