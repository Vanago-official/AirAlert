import logging
from os import getenv

import configparser
from dotenv import load_dotenv

load_dotenv()

from alerts_in_ua import AsyncClient  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.cfg")

token = getenv("ALARM")
CITY = config["Settings"]["CITY"]

# Persistent client instance for caching and rate limit handling
_client = AsyncClient(token=token)


async def get_alert():
    try:
        alerts = await _client.get_active_alerts()
        city_alerts = alerts.get_alerts_by_location_title(CITY)

        if not city_alerts:
            return False, [], None

        # alert_level and threats are not parsed by the library,
        # so we fetch them from the raw cached response
        raw_alerts = _client.cache.get("alerts/active.json", {}).get("Data", {})
        raw_list = raw_alerts.get("alerts", [])
        raw_city = next(
            (a for a in raw_list if a.get("location_title") == CITY), None
        )

        if raw_city is None:
            return False, [], None

        alert_level = raw_city.get("alert_level")
        alert_type = raw_city.get("alert_type")
        threats = raw_city.get("threats") or []
        threat_types = [
            t.get("threat_type") for t in threats if t.get("threat_type")
        ]

        return alert_level, threat_types, alert_type

    except Exception as e:  # noqa: BLE001
        logger.error(f"[API ERROR] Failed to check alert: {e}")
        return False, [], None
