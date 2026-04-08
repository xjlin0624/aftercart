"""
Gemini Flash client for generating customer support messages.
"""
import logging

from google import genai

from ..core.settings import get_settings
from ..models.alert import Alert
from ..models.enums import AlertType, MessageTone
from ..models.order import Order

logger = logging.getLogger(__name__)

_TONE_INSTRUCTIONS = {
    MessageTone.polite: (
        "Write in a polite, friendly, and appreciative tone. "
        "Be respectful and express gratitude for their service."
    ),
    MessageTone.firm: (
        "Write in a firm, confident, and direct tone. "
        "Be assertive about your rights as a customer without being rude."
    ),
    MessageTone.concise: (
        "Write in a concise, to-the-point tone. "
        "Keep it short — no more than 3 sentences. No pleasantries."
    ),
}


def _build_prompt(alert: Alert, tone: MessageTone) -> str:
    tone_instruction = _TONE_INSTRUCTIONS[tone]

    if alert.alert_type == AlertType.price_drop:
        paid = alert.evidence.get("paid_price") if alert.evidence else None
        current = alert.evidence.get("current_price") if alert.evidence else None
        savings = alert.estimated_savings

        price_info = ""
        if paid and current:
            price_info = f"I paid ${paid:.2f} and the current price is ${current:.2f}"
            if savings:
                price_info += f", a difference of ${savings:.2f}"
            price_info += "."

        return (
            f"Write a customer support message to request a price match or partial refund. "
            f"The product is: {alert.title}. "
            f"{price_info} "
            f"{tone_instruction} "
            f"The message should be ready to send directly to the retailer's customer support. "
            f"Do not include a subject line. Do not include placeholder brackets."
        )

    if alert.alert_type == AlertType.delivery_anomaly:
        return (
            f"Write a customer support message to inquire about a delivery issue. "
            f"The issue is: {alert.body} "
            f"{tone_instruction} "
            f"The message should be ready to send directly to the retailer's customer support. "
            f"Do not include a subject line. Do not include placeholder brackets."
        )

    # Fallback for other alert types
    return (
        f"Write a customer support message about the following issue: {alert.body} "
        f"{tone_instruction} "
        f"The message should be ready to send directly to the retailer's customer support. "
        f"Do not include a subject line. Do not include placeholder brackets."
    )


def static_fallback_for_alert(alert: Alert) -> str:
    """Static template used when Gemini is unavailable for an alert-based message."""
    if alert.alert_type == AlertType.price_drop:
        paid = alert.evidence.get("paid_price") if alert.evidence else None
        current = alert.evidence.get("current_price") if alert.evidence else None
        price_info = (
            f" I originally paid ${paid:.2f} and the current price is ${current:.2f}."
            if paid and current else ""
        )
        return (
            f"Hello, I am writing to request a price match for {alert.title}.{price_info} "
            f"Could you please process a partial refund for the difference? Thank you."
        )
    if alert.alert_type == AlertType.delivery_anomaly:
        return (
            f"Hello, I am writing to inquire about an issue with my delivery: {alert.body} "
            f"Could you please look into this and provide an update? Thank you."
        )
    return (
        f"Hello, I am writing regarding the following issue: {alert.body} "
        f"Could you please assist me? Thank you."
    )


def static_fallback_for_order(order: Order, request_type: str) -> str:
    """Static template used when Gemini is unavailable for an order-based message."""
    item_names = ", ".join(item.product_name for item in order.items) if order.items else "my order"
    if request_type == "price_match":
        return (
            f"Hello, I recently purchased {item_names} from {order.retailer} "
            f"and noticed the price has since dropped. "
            f"I would like to request a price match for the difference. "
            f"Could you please assist me? Thank you."
        )
    if request_type == "return_request":
        deadline = f" My return deadline is {order.return_deadline}." if order.return_deadline else ""
        return (
            f"Hello, I would like to initiate a return for {item_names} purchased from {order.retailer}.{deadline} "
            f"Could you please provide instructions on how to proceed? Thank you."
        )
    return (
        f"Hello, I am writing regarding my order from {order.retailer} for {item_names}. "
        f"Could you please assist me? Thank you."
    )


def _build_order_prompt(order: Order, request_type: str, tone: MessageTone) -> str:
    tone_instruction = _TONE_INSTRUCTIONS[tone]

    item_names = ", ".join(item.product_name for item in order.items) if order.items else "my order"

    if request_type == "price_match":
        lines = [
            f"Write a customer support message to request a price match. ",
            f"Retailer: {order.retailer}. ",
            f"Items: {item_names}. ",
        ]
        # Include per-item price info if available
        for item in order.items:
            if item.paid_price and item.current_price and item.current_price < item.paid_price:
                savings = item.paid_price - item.current_price
                lines.append(
                    f"I paid ${item.paid_price:.2f} for {item.product_name} "
                    f"and it is now ${item.current_price:.2f} (a difference of ${savings:.2f}). "
                )
        lines += [
            f"{tone_instruction} ",
            f"The message should be ready to send directly to the retailer's customer support. ",
            f"Do not include a subject line. Do not include placeholder brackets.",
        ]
        return "".join(lines)

    if request_type == "return_request":
        deadline = f" My return deadline is {order.return_deadline}." if order.return_deadline else ""
        return (
            f"Write a customer support message to initiate a return. "
            f"Retailer: {order.retailer}. "
            f"Items: {item_names}.{deadline} "
            f"{tone_instruction} "
            f"The message should be ready to send directly to the retailer's customer support. "
            f"Do not include a subject line. Do not include placeholder brackets."
        )

    # Fallback
    return (
        f"Write a customer support message regarding my order from {order.retailer} "
        f"for: {item_names}. "
        f"{tone_instruction} "
        f"The message should be ready to send directly to the retailer's customer support. "
        f"Do not include a subject line. Do not include placeholder brackets."
    )


def generate_message_from_order(order: Order, request_type: str, tone: MessageTone) -> str:
    """
    Generate a customer support message from live order + item data.
    Raises RuntimeError if GEMINI_API_KEY is not configured.
    Raises RuntimeError if the Gemini API call fails.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = _build_order_prompt(order, request_type, tone)

    try:
        response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
        return response.text.strip()
    except Exception as e:
        logger.error("Gemini API call failed: %s", e)
        raise RuntimeError(f"Failed to generate message: {e}") from e


def generate_support_message(alert: Alert, tone: MessageTone) -> str:
    """
    Generate a customer support message for the given alert and tone using Gemini Flash.
    Raises RuntimeError if GEMINI_API_KEY is not configured.
    Raises RuntimeError if the Gemini API call fails.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = _build_prompt(alert, tone)

    try:
        response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
        return response.text.strip()
    except Exception as e:
        logger.error("Gemini API call failed: %s", e)
        raise RuntimeError(f"Failed to generate message: {e}") from e
