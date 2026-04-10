from fastapi import APIRouter
from sqlalchemy.orm import Session

from .deps import CurrentUser, DB
from ..models.user import User
from ..models.user_preferences import UserPreferences
from ..schemas.user_preferences import UserPreferencesRead, UserPreferencesUpdate

router = APIRouter(prefix="/users/me/preferences", tags=["preferences"])


def _get_or_create_preferences(db: Session, user: User) -> UserPreferences:
    """Return existing preferences or create defaults on first access."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user.id).first()
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("", response_model=UserPreferencesRead)
def get_preferences(db: DB, current_user: CurrentUser) -> UserPreferences:
    return _get_or_create_preferences(db, current_user)


@router.patch("", response_model=UserPreferencesRead)
def update_preferences(
    body: UserPreferencesUpdate,
    db: DB,
    current_user: CurrentUser,
) -> UserPreferences:
    prefs = _get_or_create_preferences(db, current_user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)
    return prefs
