from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from .deps import CurrentUser, DB
from ..models.enums import MessageTone
from ..models.order import Order
from ..services.gemini import generate_message_from_order, static_fallback_for_order

router = APIRouter(prefix="/messages", tags=["messages"])

_VALID_REQUEST_TYPES = {"price_match", "return_request"}


class MessageGenerateRequest(BaseModel):
    order_id: UUID
    request_type: str   # "price_match" or "return_request"
    tone: MessageTone = MessageTone.polite


class MessageGenerateResponse(BaseModel):
    order_id: UUID
    request_type: str
    tone: str
    message: str
    fallback: bool = False


@router.post("/generate", response_model=MessageGenerateResponse)
def generate_order_message(
    body: MessageGenerateRequest,
    db: DB,
    current_user: CurrentUser,
) -> MessageGenerateResponse:
    """
    Generate a customer support message from live order context.

    request_type: "price_match" or "return_request"
    tone: polite | firm | concise (defaults to polite)

    Returns 404 if the order does not exist or belongs to another user.
    Returns 400 if request_type is invalid.
    Returns 503 if Gemini is unavailable.
    """
    if body.request_type not in _VALID_REQUEST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request_type. Must be one of: {', '.join(sorted(_VALID_REQUEST_TYPES))}",
        )

    order = db.get(Order, body.order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if body.request_type == "price_match" and not any(
        item.current_price is not None and item.current_price < item.paid_price
        for item in order.items
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price drop detected on any item in this order",
        )

    is_fallback = False
    try:
        message = generate_message_from_order(order, body.request_type, body.tone)
    except RuntimeError:
        message = static_fallback_for_order(order, body.request_type)
        is_fallback = True

    return MessageGenerateResponse(
        order_id=body.order_id,
        request_type=body.request_type,
        tone=body.tone.value,
        message=message,
        fallback=is_fallback,
    )
