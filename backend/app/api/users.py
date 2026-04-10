from fastapi import APIRouter

from .deps import CurrentUser
from ..models.user import User
from ..schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> User:
    """Return the authenticated user's profile."""
    return current_user
