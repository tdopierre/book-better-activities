import datetime
from pydantic import BaseModel


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
