import datetime
import logging

from src.booking import execute_booking_with_fallback
from src.clients.better_client import get_client
from src.config import ScheduledBookingConfig

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def run_scheduled_booking(scheduled: ScheduledBookingConfig) -> None:
    """Wrapper to run a scheduled booking with fallback attempts."""
    activity_date = datetime.date.today() + datetime.timedelta(
        days=scheduled.days_ahead
    )
    webhook_url = (
        scheduled.discord_webhook_url.get_secret_value()
        if scheduled.discord_webhook_url
        else None
    )
    execute_booking_with_fallback(
        attempts=scheduled.attempts,
        activity_date=activity_date,
        job_name=scheduled.name,
        discord_webhook_url=webhook_url,
    )


def validate_credentials(bookings: list[ScheduledBookingConfig]) -> None:
    """Validate all unique credential pairs across all booking attempts."""
    seen = set()
    for booking in bookings:
        for attempt in booking.attempts:
            key = (attempt.username, attempt.password.get_secret_value())
            if key in seen:
                continue
            seen.add(key)

            logger.info(f"Validating credentials for {attempt.username}...")
            client = get_client(
                username=attempt.username,
                password=attempt.password,  # Pass SecretStr directly
            )
            client.authenticate()
            logger.info(f"✓ Credentials valid for {attempt.username}")


def convert_cron_dow_to_apscheduler(dow: str) -> str:
    """Convert standard cron day-of-week to APScheduler format.

    Standard cron: 0=Sun, 1=Mon, ..., 6=Sat
    APScheduler:   0=Mon, 1=Tue, ..., 6=Sun
    """
    # Map cron DOW (0-6, Sun-Sat) to APScheduler (0-6, Mon-Sun)
    cron_to_aps = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}

    def convert_single(val: str) -> str:
        if val == "*":
            return val
        return str(cron_to_aps[int(val)])

    # Handle ranges like "1-5"
    if "-" in dow:
        start, end = dow.split("-")
        return f"{convert_single(start)}-{convert_single(end)}"
    # Handle lists like "1,3,5"
    elif "," in dow:
        return ",".join(convert_single(v) for v in dow.split(","))
    else:
        return convert_single(dow)


def parse_cron_expression(cron_expr: str) -> dict:
    """Parse a cron expression into APScheduler CronTrigger kwargs."""
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    minute, hour, day, month, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "day_of_week": convert_cron_dow_to_apscheduler(day_of_week),
    }
