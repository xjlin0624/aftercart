from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from .deps import CurrentUser, DB
from ..models.push_device_token import PushDeviceToken
from ..schemas.push_token import PushTokenRead, PushTokenUpsert


router = APIRouter(prefix="/push/tokens", tags=["push"])


@router.post("", response_model=PushTokenRead, status_code=status.HTTP_201_CREATED)
def register_push_token(
    body: PushTokenUpsert,
    db: DB,
    current_user: CurrentUser,
) -> PushDeviceToken:
    token = db.execute(
        select(PushDeviceToken).where(PushDeviceToken.token == body.token)
    ).scalar_one_or_none()

    if token is None:
        token = PushDeviceToken(
            user_id=current_user.id,
            token=body.token,
            platform=body.platform,
            browser=body.browser,
            is_active=True,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(token)
    else:
        token.user_id = current_user.id
        token.platform = body.platform
        token.browser = body.browser
        token.is_active = True
        token.last_seen_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(token)
    return token


@router.delete("/{token:path}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_push_token(
    token: str,
    db: DB,
    current_user: CurrentUser,
) -> Response:
    stored = db.execute(
        select(PushDeviceToken)
        .where(PushDeviceToken.token == token)
        .where(PushDeviceToken.user_id == current_user.id)
    ).scalar_one_or_none()
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push token not found")

    stored.is_active = False
    stored.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
