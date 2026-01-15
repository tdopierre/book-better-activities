import argparse
import logging
import os

from pydantic import SecretStr
from src.clients.better_client import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="List your bookings")
    parser.add_argument(
        "--filter",
        choices=["future", "past", "all"],
        default="future",
        help="Filter bookings by time (default: future)",
    )
    args = parser.parse_args()

    username = os.environ.get("BETTER_USERNAME")
    password = os.environ.get("BETTER_PASSWORD")

    if not username or not password:
        raise ValueError("BETTER_USERNAME and BETTER_PASSWORD must be set")

    client = get_client(username=username, password=SecretStr(password))

    bookings = client.get_my_bookings(filter=args.filter)

    if not bookings:
        logger.info(f"No {args.filter} bookings found")
        return

    logger.info(f"Found {len(bookings)} {args.filter} booking(s):")
    print()

    for booking in bookings:
        print(f"Booking ID: {booking.id}")
        print(f"  Activity: {booking.simple_name}")
        print(f"  Venue: {booking.venue}")
        print(f"  Location: {booking.item.location.name}")
        print(f"  Date/Time: {booking.date} at {booking.time}")
        print(f"  Price: {booking.price}")
        print(f"  Status: {booking.status}")
        print(f"  Can Cancel: {'Yes' if booking.can_be_cancelled else 'No'}")
        print(f"  Order ID: {booking.order_id}")
        print()


if __name__ == "__main__":
    main()
