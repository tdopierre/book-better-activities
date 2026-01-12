import argparse
import datetime
import logging
import os

from src.clients.better_client import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="List available activity slots")
    parser.add_argument("--venue", required=True, help="Venue slug")
    parser.add_argument("--activity", required=True, help="Activity slug")
    parser.add_argument("--date", required=True, help="Activity date (YYYY-MM-DD)")
    args = parser.parse_args()

    username = os.environ.get("BETTER_USERNAME")
    password = os.environ.get("BETTER_PASSWORD")

    if not username or not password:
        raise ValueError("BETTER_USERNAME and BETTER_PASSWORD must be set")

    activity_date = datetime.date.fromisoformat(args.date)

    client = get_client(username=username, password=password)

    activity_times = client.get_available_times_for(
        venue=args.venue,
        activity=args.activity,
        activity_date=activity_date,
    )

    if not activity_times:
        logger.info("No available slots found")
        return

    logger.info(f"Found {len(activity_times)} available time slots:")
    for t in activity_times:
        print(
            f"  {t.start}-{t.end} | {t.name} | {t.location} | {t.spaces} spaces | {t.price}"
        )


if __name__ == "__main__":
    main()
