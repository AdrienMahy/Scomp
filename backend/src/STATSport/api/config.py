"""Configuration for the STATSports V7 API."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class StatsportSettings:
    """Runtime settings for the isolated STATSports client."""

    api_token: str = ""
    api_base_url: str = "https://statsportsproseries.com/thirdpartyapi/api/thirdPartyData"
    api_version: str = "7"
    timeout_seconds: float = 90.0

    @classmethod
    def from_env(cls) -> "StatsportSettings":
        return cls(
            api_token=os.getenv("STATSPORT_API_TOKEN", ""),
            api_base_url=os.getenv(
                "STATSPORT_API_BASE_URL",
                "https://statsportsproseries.com/thirdpartyapi/api/thirdPartyData",
            ).rstrip("/"),
            api_version=os.getenv("STATSPORT_API_VERSION", "7"),
            timeout_seconds=float(os.getenv("STATSPORT_API_TIMEOUT", "90")),
        )
