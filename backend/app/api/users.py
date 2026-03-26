from typing import Annotated

from fastapi import APIRouter, Depends

from .deps import get_current_user
from ..models.user import User
from ..schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> User:
    """Return the authenticated user's profile."""
    return current_user
