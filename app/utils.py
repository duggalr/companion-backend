from sqlalchemy.orm import Session
from app.models import AnonUser, CustomUser


def _check_if_anon_user_exists(
    anon_user_id: str,
    db: Session
):
    anon_user_object = db.query(CustomUser).filter(
        CustomUser.anon_user_id == anon_user_id
    ).first()
    if anon_user_object is None:
        return False
    return True

def create_anon_user_object(anon_user_id: str, db: Session) -> CustomUser:
    if _check_if_anon_user_exists():
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

