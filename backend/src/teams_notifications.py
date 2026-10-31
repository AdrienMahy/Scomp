"""Best-effort Teams notifications for completed scraping runs."""

import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)

WEBHOOK_ENV_VARS = {
    "physical": "TEAMS_PHYSICAL_WEBHOOK_URL",
    "tactical": "TEAMS_TACTICAL_WEBHOOK_URL",
}


def _send_teams_payload(channel: str, payload: dict[str, Any]) -> bool:
    env_var = WEBHOOK_ENV_VARS.get(channel)
    webhook_url = os.getenv(env_var, "").strip() if env_var else ""
    if not webhook_url:
        return False

    try:
        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
    except Exception as error:
        logger.warning("Teams notification for %s failed (%s)", channel, type(error).__name__)
        return False
    return True


def send_teams_notification(channel: str, message: str) -> bool:
    return _send_teams_payload(channel, {"text": message})


def send_teams_adaptive_card(channel: str, card: dict[str, Any]) -> bool:
    return _send_teams_payload(channel, card)