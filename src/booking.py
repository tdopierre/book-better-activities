import datetime
import logging

from src.config import BookingConfig
from src.clients.better_client import get_client
from src.exceptions import NotEnoughSlotsFound

logger = logging.getLogger(__name__)


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
