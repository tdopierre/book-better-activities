import datetime
import logging

from src.config import BookingConfig
from src.clients.better_client import get_client
from src.exceptions import AllBookingAttemptsFailed, NotEnoughSlotsFound

logger = logging.getLogger(__name__)


def parse_time_window(
    min_slot_time: str, max_slot_time: str | None
) -> tuple[datetime.time, datetime.time | None]:
    """Parse time strings into time objects."""
    min_time = datetime.time.fromisoformat(min_slot_time)
    max_time = datetime.time.fromisoformat(max_slot_time) if max_slot_time else None
    return min_time, max_time


def filter_slots_by_time_window(
    activity_times: list,
    min_time: datetime.time,
    max_time: datetime.time | None,
) -> list:
    """Filter slots to be within time window."""
    filtered = [s for s in activity_times if s.start >= min_time]
    if max_time:
        filtered = [s for s in filtered if s.end <= max_time]
    return filtered


def convert_times_to_slots(
    client,
    venue: str,
    activity: str,
    activity_date: datetime.date,
    activity_times: list,
) -> list:
    """Convert ActivityTime objects to bookable ActivitySlot objects."""
    slots = []
    for activity_time in activity_times:
        slot_list = client.get_available_slots_for(
            venue=venue,
            activity=activity,
            activity_date=activity_date,
            start_time=activity_time.start,
            end_time=activity_time.end,
        )
        slots.append(slot_list[0])
    return slots


def complete_booking(client, slots: list) -> str:
    """Add slots to cart and checkout. Returns order_id."""
    cart = client.add_to_cart(slots)
    order_id = client.checkout_with_benefit(cart=cart)
    return order_id


def log_attempt_start(attempt_num: int, total: int, attempt) -> None:
    """Log start of booking attempt."""
    logger.info(
        f"Attempt {attempt_num}/{total}: "
        f"venue={attempt.venue}, activity={attempt.activity}, "
        f"time={attempt.min_slot_time}-{attempt.max_slot_time or 'any'}, "
        f"n_slots={attempt.n_slots}"
    )


def log_attempt_success(job_name: str, attempt_num: int, order_id: str) -> None:
    """Log successful booking."""
    logger.info(
        f"[{job_name}] ✓ SUCCESS! Attempt {attempt_num} succeeded. Order ID: {order_id}"
    )


def log_attempt_failure(job_name: str, attempt_num: int, error: Exception) -> None:
    """Log failed attempt."""
    logger.warning(
        f"[{job_name}] ✗ Attempt {attempt_num} failed: {type(error).__name__}: {error}"
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


def book_activity_slots(
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


def execute_single_attempt(
    attempt,
    activity_date: datetime.date,
    attempt_number: int,
    total_attempts: int,
) -> dict[str, any]:
    """
    Execute a single booking attempt.

    Returns:
        dict with keys: 'success' (bool), 'order_id' (str|None), 'error' (Exception|None)
    """
    log_attempt_start(attempt_number, total_attempts, attempt)

    try:
        # Parse time window
        min_time, max_time = parse_time_window(
            attempt.min_slot_time, attempt.max_slot_time
        )

        # Authenticate and get client
        client = get_client(username=attempt.username, password=attempt.password)

        # Fetch available times
        available_times = client.get_available_times_for(
            venue=attempt.venue,
            activity=attempt.activity,
            activity_date=activity_date,
        )
        times_str = ", ".join(f"{t.start}-{t.end}" for t in available_times)
        logger.info(
            f"Attempt {attempt_number}: Found {len(available_times)} times: {times_str}"
        )

        # Filter by time window
        filtered_times = filter_slots_by_time_window(
            activity_times=available_times,
            min_time=min_time,
            max_time=max_time,
        )
        times_str = ", ".join(f"{t.start}-{t.end}" for t in filtered_times)
        logger.info(
            f"Attempt {attempt_number}: After filtering, {len(filtered_times)} times: {times_str}"
        )

        # Find consecutive slots
        consecutive = find_consecutive_slots(filtered_times, attempt.n_slots)
        if not consecutive:
            raise NotEnoughSlotsFound(
                f"Could not find {attempt.n_slots} consecutive slots"
            )
        logger.info(
            f"Attempt {attempt_number}: Found consecutive slots: "
            f"{consecutive[0].start} - {consecutive[-1].end}"
        )

        # Convert to bookable slots and complete booking
        slots = convert_times_to_slots(
            client=client,
            venue=attempt.venue,
            activity=attempt.activity,
            activity_date=activity_date,
            activity_times=consecutive,
        )
        order_id = complete_booking(client=client, slots=slots)

        return {"success": True, "order_id": order_id, "error": None}

    except Exception as e:
        return {"success": False, "order_id": None, "error": e}


def execute_booking_with_fallback(
    attempts: list,
    activity_date: datetime.date,
    job_name: str,
) -> str:
    """
    Try booking attempts in order until one succeeds.

    Returns:
        order_id of successful booking

    Raises:
        AllBookingAttemptsFailed if all attempts fail
    """
    logger.info(f"[{job_name}] Starting booking with {len(attempts)} attempt(s)")
    all_errors = []

    for idx, attempt in enumerate(attempts):
        attempt_num = idx + 1
        result = execute_single_attempt(
            attempt=attempt,
            activity_date=activity_date,
            attempt_number=attempt_num,
            total_attempts=len(attempts),
        )

        if result["success"]:
            log_attempt_success(job_name, attempt_num, result["order_id"])
            return result["order_id"]
        else:
            log_attempt_failure(job_name, attempt_num, result["error"])
            all_errors.append((idx, result["error"]))

    # All attempts failed
    logger.error(
        f"[{job_name}] All {len(attempts)} attempt(s) failed. No booking made."
    )
    raise AllBookingAttemptsFailed(job_name, all_errors)
