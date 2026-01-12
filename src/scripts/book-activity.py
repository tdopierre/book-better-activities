import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import load_config, BookingConfig
from src.clients.better_client import get_client
from src.exceptions import NotEnoughSlotsFound

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def book_activity(booking: BookingConfig) -> None:
    """Execute a single booking job."""
    logger.info(f"Starting booking job: {booking.name}")

    try:
        activity_date = datetime.datetime.today() + datetime.timedelta(
            days=booking.days_ahead
        )
        min_slot_time = datetime.time.fromisoformat(booking.min_slot_time)

        client = get_client(username=booking.username, password=booking.password)

        activity_times = client.get_available_times_for(
            venue=booking.venue,
            activity=booking.activity,
            activity_date=activity_date,
        )
        logger.info(f"[{booking.name}] Found {len(activity_times)} activity times")

        activity_times = [s for s in activity_times if s.start >= min_slot_time]
        logger.info(
            f"[{booking.name}] After filtering, got {len(activity_times)} activity times"
        )

        if len(activity_times) < booking.n_slots:
            raise NotEnoughSlotsFound(
                f"[{booking.name}] Only got {len(activity_times)} activity_times, need {booking.n_slots}"
            )

        cart = None
        for activity_time in activity_times[: booking.n_slots]:
            slots = client.get_available_slots_for(
                venue=booking.venue,
                activity=booking.activity,
                activity_date=activity_date,
                start_time=activity_time.start,
                end_time=activity_time.end,
            )
            cart = client.add_to_cart(slots[0])

        if cart:
            order_id = client.checkout_with_benefit(cart=cart)
            logger.info(f"[{booking.name}] Successfully booked! Order ID: {order_id}")

    except Exception as e:
        logger.error(f"[{booking.name}] Booking failed: {e}")
        raise


def validate_credentials(bookings: list[BookingConfig]) -> None:
    """Validate all unique credential pairs at startup."""
    seen = set()
    for booking in bookings:
        key = (booking.username, booking.password)
        if key in seen:
            continue
        seen.add(key)

        logger.info(f"Validating credentials for {booking.username}...")
        client = get_client(username=booking.username, password=booking.password)
        client.authenticate()
        logger.info(f"Credentials valid for {booking.username}")


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
            book_activity,
            trigger=trigger,
            args=[booking],
            id=booking.name,
            name=booking.name,
        )
        now = datetime.datetime.now(ZoneInfo("Europe/London"))
        next_run = trigger.get_next_fire_time(None, now)
        logger.info(f"Scheduled job: {booking.name} (next run: {next_run})")

    logger.info(f"Starting scheduler with {len(config.bookings)} job(s)")
    scheduler.start()


if __name__ == "__main__":
    main()
