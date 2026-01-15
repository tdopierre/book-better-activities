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
    name: str
    location: str
    spaces: int
    price: str | None
    duration: str


class ActivityCart(BaseModel):
    id: int
    amount: int
    source: str


class BookingLocation(BaseModel):
    id: str
    name: str
    type: str
    slug: str
    venue_id: int
    venue_slug: str


class BookingItem(BaseModel):
    duration: str
    location: BookingLocation


class Booking(BaseModel):
    id: int
    can_be_cancelled: bool
    status: str
    category: str
    venue: str
    venue_name: str
    simple_name: str
    price: str
    date: str
    time: str
    description: str
    order_id: int
    activity_id: int
    item: BookingItem
