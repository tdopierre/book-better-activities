import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import load_config, BookingConfig, ScheduledBookingConfig
from src.clients.better_client import get_client
from src.exceptions import NotEnoughSlotsFound

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def find_consecutive_slots(activity_times: list, n_slots: int) -> list | None:
    """Find n consecutive slots where each slot starts when the previous ends."""
    if len(activity_times) < n_slots:
        return None

    for i in range(len(activity_times) - n_slots + 1):
        candidate = activity_times[i : i + n_slots]
        is_consecutive = all(
            candidate[j].end == candidate[j + 1].start
            for j in range(len(candidate) - 1)
        )
        if is_consecutive:
            return candidate

    return None


def book_activity(
    booking: BookingConfig,
    activity_date: datetime.date,
    name: str = "booking",
) -> None:
    """Execute a single booking job."""
    logger.info(f"Starting booking job: {name}")

    try:
        min_slot_time = datetime.time.fromisoformat(booking.min_slot_time)
        max_slot_time = (
            datetime.time.fromisoformat(booking.max_slot_time)
            if booking.max_slot_time
            else None
        )

        client = get_client(username=booking.username, password=booking.password)

        activity_times = client.get_available_times_for(
            venue=booking.venue,
            activity=booking.activity,
            activity_date=activity_date,
        )
        times_str = ", ".join(f"{t.start}-{t.end}" for t in activity_times)
        logger.info(f"[{name}] Found {len(activity_times)} activity times: {times_str}")

        # Filter by min_slot_time
        activity_times = [s for s in activity_times if s.start >= min_slot_time]

        # Filter by max_slot_time (slot must end by max_slot_time)
        if max_slot_time:
            activity_times = [s for s in activity_times if s.end <= max_slot_time]

        times_str = ", ".join(f"{t.start}-{t.end}" for t in activity_times)
        logger.info(
            f"[{name}] After filtering, got {len(activity_times)} activity times: {times_str}"
        )

        # Find consecutive slots
        consecutive_slots = find_consecutive_slots(activity_times, booking.n_slots)
        if not consecutive_slots:
            raise NotEnoughSlotsFound(
                f"[{name}] Could not find {booking.n_slots} consecutive slots"
            )

        logger.info(
            f"[{name}] Found consecutive slots: "
            f"{consecutive_slots[0].start} - {consecutive_slots[-1].end}"
        )

        slots_to_book = []
        for activity_time in consecutive_slots:
            slots = client.get_available_slots_for(
                venue=booking.venue,
                activity=booking.activity,
                activity_date=activity_date,
                start_time=activity_time.start,
                end_time=activity_time.end,
            )
            slots_to_book.append(slots[0])

        if slots_to_book:
            cart = client.add_to_cart(slots_to_book)
            order_id = client.checkout_with_benefit(cart=cart)
            logger.info(f"[{name}] Successfully booked! Order ID: {order_id}")

    except Exception as e:
        logger.error(f"[{name}] Booking failed: {e}")
        raise


def run_scheduled_booking(scheduled: ScheduledBookingConfig) -> None:
    """Wrapper to run a scheduled booking."""
    activity_date = datetime.date.today() + datetime.timedelta(
        days=scheduled.days_ahead
    )
    book_activity(
        booking=scheduled,
        activity_date=activity_date,
        name=scheduled.name,
    )


def validate_credentials(bookings: list[ScheduledBookingConfig]) -> None:
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
