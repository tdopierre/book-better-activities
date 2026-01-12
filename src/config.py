from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Base app settings."""

    better_username: str = Field(description="Better username")
    better_password: SecretStr = Field(description="Better password")


app_config = AppConfig()
