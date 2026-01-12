import datetime
from typing import Annotated
import typer
from src import models
from src.clients.better_client import get_client
from src.exceptions import NotEnoughSlotsFound

import logging

logger = logging.getLogger(__name__)


def main(
    venue: Annotated[models.BetterVenue, typer.Option(help="Venue")],
    activity: Annotated[models.BetterActivity, typer.Option(help="Activity")],
    min_slot_time: Annotated[str, typer.Option(help="Min slot time (HH:MM:SS)")],
    n_slots: Annotated[int, typer.Option(help="Number of consecutive slots to book")],
):
    """Book an activity."""
    # Book 1 week from now
    # venue = models.BetterVenue.queensbridge
    # activity = models.BetterActivity.badminton_40_mins
    # min_slot_time="16:01:00"
    activity_date = datetime.datetime.today() + datetime.timedelta(days=4)
    min_slot_time = datetime.time.fromisoformat(min_slot_time)
    n_slots = 2
    # Create client
    client = get_client()

    # Get times
    activity_times = client.get_available_times_for(
        venue=venue, activity=activity, activity_date=activity_date
    )
    logger.info(f"Found {len(activity_times)} activity times")
    activity_times = [s for s in activity_times if s.start >= min_slot_time]

    logger.info(f"After filtering, got {len(activity_times)} activity times")

    if len(activity_times) < n_slots:
        raise NotEnoughSlotsFound(f"Only got {len(activity_times)} activity_times")

    for activity_time in activity_times[:n_slots]:
        slots = client.get_available_slots_for(
            venue=venue,
            activity=activity,
            activity_date=activity_date,
            start_time=activity_time.start,
            end_time=activity_time.end,
        )
        cart = client.add_to_cart(slots[0])

    client.checkout_with_benefit(cart=cart)
