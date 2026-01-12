from __future__ import annotations

import datetime
import functools
import logging
from collections.abc import Callable
from typing import Concatenate

from pydantic import SecretStr
from httpx_retries import RetryTransport, Retry
import httpx
from src.models import (
    ActivityCart,
    ActivitySlot,
    ActivityTime,
)

type _LiveBetterClientInstanceMethod[**P, R] = Callable[
    Concatenate[LiveBetterClient, P], R
]


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def _requires_authentication[**P, R](
    func: _LiveBetterClientInstanceMethod[P, R],
) -> _LiveBetterClientInstanceMethod[P, R]:
    @functools.wraps(func)
    def wrapper(self: LiveBetterClient, *args: P.args, **kwargs: P.kwargs) -> R:
        if not self.authenticated:
            logging.info(
                "requires_authentication: client is not authenticated, will authenticate"
            )
            self.authenticate()
        return func(self, *args, **kwargs)

    return wrapper


class LiveBetterClient:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "application/json",
        "Accept-Language": "en-GB,en;q=0.5",
        # 'Accept-Encoding': 'gzip, deflate, br, zstd',
        "Content-Type": "application/json",
        "Origin": "https://myaccount.better.org.uk",
        "Connection": "keep-alive",
        "Referer": "https://myaccount.better.org.uk/",
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }

    def __init__(self, username: str, password: SecretStr):
        self.username = username
        self.password = password

        retry = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        self.client = httpx.Client(
            base_url="https://better-admin.org.uk/api/",
            transport=RetryTransport(retry=retry),
            timeout=30.0,
        )
        self.client.headers.update(self.HEADERS)

    @property
    def authenticated(self) -> bool:
        return bool(self.client.headers.get("Authorization"))

    @functools.cached_property
    @_requires_authentication
    def membership_user_id(self) -> int:
        response = self.client.get("auth/user")
        response.raise_for_status()

        return response.json()["data"]["membership_user"]["id"]

    def authenticate(self) -> None:
        logger.info(f"Authenticating user {self.username}...")
        auth_response = self.client.post(
            "auth/customer/login",
            json=dict(
                username=self.username, password=self.password.get_secret_value()
            ),
        )
        auth_response.raise_for_status()

        token: str = auth_response.json()["token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @_requires_authentication
    def get_available_slots_for(
        self,
        venue: str,
        activity: str,
        activity_date: datetime.date,
        start_time: datetime.time,
        end_time: datetime.time,
    ) -> list[ActivitySlot]:
        response = self.client.get(
            f"activities/venue/{venue}/activity/{activity}/slots",
            params={
                "date": activity_date.strftime("%Y-%m-%d"),
                "start_time": start_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
            },
        )
        response.raise_for_status()

        return [
            ActivitySlot(
                id=slot["id"],
                location_id=slot["location"]["id"],
                pricing_option_id=slot["pricing_option_id"],
                restriction_ids=slot["restriction_ids"],
                name=slot["location"]["slug"],
                cart_type=slot["cart_type"],
            )
            for slot in response.json()["data"]
            if slot["spaces"] > 0 and slot["booking"] is None
            # and slot["benefit_available"] is not None
        ]

    @_requires_authentication
    def get_available_times_for(
        self, venue: str, activity: str, activity_date: datetime.date
    ) -> list[ActivityTime]:
        response = self.client.get(
            f"activities/venue/{venue}/activity/{activity}/times",
            params={"date": activity_date.strftime("%Y-%m-%d")},
        )
        response.raise_for_status()

        data = response.json()["data"]
        logger.info(data)
        return [
            ActivityTime(
                start=datetime.datetime.strptime(
                    time_["starts_at"]["format_24_hour"], "%H:%M"
                ).time(),
                end=datetime.datetime.strptime(
                    time_["ends_at"]["format_24_hour"], "%H:%M"
                ).time(),
                name=time_["name"],
                location=time_["location"],
                spaces=time_["spaces"],
                price=time_["price"]["formatted_amount"],
                duration=time_["duration"],
            )
            for time_ in data
            if time_["spaces"] > 0 and time_["booking"] is None
        ]

    @_requires_authentication
    def add_to_cart(self, slots: list[ActivitySlot]) -> ActivityCart:
        response = self.client.post(
            "activities/cart/add",
            json=dict(
                items=[
                    dict(
                        activity_restriction_ids=slot.restriction_ids,
                        apply_benefit=True,
                        id=slot.id,
                        pricing_option_id=slot.pricing_option_id,
                        type=slot.cart_type,
                    )
                    for slot in slots
                ],
                membership_user_id=self.membership_user_id,
                selected_user_id=None,
            ),
        )
        response.raise_for_status()

        data = response.json()["data"]

        return ActivityCart(
            id=data["id"],
            amount=data["total"],
            source=data["source"],
        )

    @_requires_authentication
    def checkout_with_benefit(self, cart: ActivityCart) -> int:
        # When need to use credit
        if cart.amount:
            apply_credits_response = self.client.post(
                "credits/apply",
                json={
                    "credits_to_reserve": [{"amount": cart.amount, "type": "general"}],
                    "cart_source": cart.source,
                    "selected_user_id": None,
                },
            )
            apply_credits_response.raise_for_status()
            payments = [{"tender_type": "credit", "amount": cart.amount}]
        else:
            payments = []

        complete_checkout_response = self.client.post(
            "checkout/complete",
            json=dict(
                completed_waivers=[],
                payments=payments,
                selected_user_id=None,
                source=cart.source,
                terms=[1],
            ),
        )
        complete_checkout_response.raise_for_status()

        return complete_checkout_response.json()["complete_order_id"]


def get_client(username: str, password: SecretStr) -> LiveBetterClient:
    """Get client with credentials."""
    return LiveBetterClient(username=username, password=password)
