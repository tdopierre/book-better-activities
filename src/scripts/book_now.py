import argparse
import datetime
import logging
import os

from src.config import BookingConfig
from src.scripts.book_activity import book_activity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Book an activity immediately")
    parser.add_argument("--venue", required=True, help="Venue slug")
    parser.add_argument("--activity", required=True, help="Activity slug")
    parser.add_argument("--date", required=True, help="Activity date (YYYY-MM-DD)")
    parser.add_argument(
        "--min-slot-time", required=True, help="Min slot time (HH:MM:SS)"
    )
    parser.add_argument(
        "--max-slot-time", default=None, help="Max slot time (HH:MM:SS)"
    )
    parser.add_argument(
        "--n-slots", type=int, default=1, help="Number of consecutive slots"
    )
    args = parser.parse_args()

    username = os.environ.get("BETTER_USERNAME")
    password = os.environ.get("BETTER_PASSWORD")

    if not username or not password:
        raise ValueError("BETTER_USERNAME and BETTER_PASSWORD must be set")

    activity_date = datetime.date.fromisoformat(args.date)

    if activity_date < datetime.date.today():
        raise ValueError(f"Date {args.date} is in the past")

    booking = BookingConfig(
        username=username,
        password=password,
        venue=args.venue,
        activity=args.activity,
        min_slot_time=args.min_slot_time,
        max_slot_time=args.max_slot_time,
        n_slots=args.n_slots,
    )

    logger.info(
        f"Booking {args.n_slots} slot(s) at {args.venue} for {args.activity} on {args.date}"
    )
    book_activity(booking=booking, activity_date=activity_date, name="one-shot")
    logger.info("Booking complete!")


if __name__ == "__main__":
    main()
