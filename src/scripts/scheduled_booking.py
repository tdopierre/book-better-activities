import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import load_config, ScheduledBookingConfig
from src.clients.better_client import get_client
from src.booking import execute_booking_with_fallback

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
    execute_booking_with_fallback(
        attempts=scheduled.attempts,
        activity_date=activity_date,
        job_name=scheduled.name,
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
                password=attempt.password.get_secret_value(),
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


def main() -> None:
    """Main entry point - load config and start scheduler."""
    config = load_config()

    if not config.bookings:
        logger.warning("No bookings configured in config.yaml")
        return

    # Validate credentials before starting scheduler
    validate_credentials(config.bookings)

    scheduler = BlockingScheduler()

    for booking in config.bookings:
        cron_kwargs = parse_cron_expression(booking.schedule)
        trigger = CronTrigger(**cron_kwargs, timezone="Europe/London")

        scheduler.add_job(
            run_scheduled_booking,
            trigger=trigger,
            args=[booking],
            id=booking.name,
            name=booking.name,
        )
        now = datetime.datetime.now(ZoneInfo("Europe/London"))
        next_run = trigger.get_next_fire_time(None, now)
        booking_date = next_run.date() + datetime.timedelta(days=booking.days_ahead)
        logger.info(
            f"Scheduled job: {booking.name} (next run: {next_run}, booking for: {booking_date})"
        )

    logger.info(f"Starting scheduler with {len(config.bookings)} job(s)")
    scheduler.start()


if __name__ == "__main__":
    main()
