"""
Gemini Flash client for generating customer support messages.
"""
import logging

from google import genai

from ..core.settings import get_settings
from ..models.alert import Alert
from ..models.enums import AlertType, MessageTone

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
