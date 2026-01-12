import enum
import datetime
from pydantic import BaseModel


class BetterVenue(enum.StrEnum):
    queensbridge = "queensbridge-sports-community-centre"
    britania = "britannia-leisure-centre"


class BetterActivity(enum.StrEnum):
    badminton_40_mins = "badminton-40min"


class ActivitySlot(BaseModel):
    id: int
    location_id: int
    pricing_option_id: int
    restriction_ids: list[int]
    name: str
    cart_type: str


class ActivityTime(BaseModel):
    start: datetime.time
    end: datetime.time


class ActivityCart(BaseModel):
    id: int
    amount: int
    source: str
