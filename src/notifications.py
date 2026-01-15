"""Discord notification functions."""

import datetime
import logging

import httpx

logger = logging.getLogger(__name__)


def send_discord_notification(webhook_url: str, message: str, color: int) -> None:
    """
    Send a notification to Discord via webhook.

    Args:
        webhook_url: Discord webhook URL
        message: Message content to send
        color: Embed color (decimal format, e.g., 0x00FF00 for green)
    """
    if not webhook_url:
        return

    try:
        embed = {
            "description": message,
            "color": color,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        payload = {"embeds": [embed]}

        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info("Discord notification sent successfully")

    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")


def send_success_notification(
    webhook_url: str | None, job_name: str, attempt_num: int, order_id: str
) -> None:
    """Send a success notification to Discord."""
    if not webhook_url:
        return

    message = (
        f"**Booking Successful!** ✅\n\n"
        f"**Job:** {job_name}\n"
        f"**Attempt:** {attempt_num}\n"
        f"**Order ID:** {order_id}"
    )

    # Green color
    send_discord_notification(webhook_url, message, 0x00FF00)


def send_failure_notification(
    webhook_url: str | None,
    job_name: str,
    total_attempts: int,
    errors: list[tuple[int, Exception]],
) -> None:
    """Send a failure notification to Discord when all attempts fail."""
    if not webhook_url:
        return

    error_details = "\n".join(
        f"• Attempt {idx + 1}: {type(err).__name__} - {err}"
        for idx, err in errors[
            :5
        ]  # Limit to first 5 errors to avoid message being too long
    )

    if len(errors) > 5:
        error_details += f"\n... and {len(errors) - 5} more error(s)"

    message = (
        f"**Booking Failed!** ❌\n\n"
        f"**Job:** {job_name}\n"
        f"**Total Attempts:** {total_attempts}\n\n"
        f"**Errors:**\n{error_details}"
    )

    # Red color
    send_discord_notification(webhook_url, message, 0xFF0000)
