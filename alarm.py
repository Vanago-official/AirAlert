import configparser
import logging
from os import getenv

from dotenv import load_dotenv

load_dotenv()

from alerts_in_ua import AsyncClient  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.cfg")

token = getenv("ALARM")
CITY = config["Settings"]["CITY"]

# Every alert kind the bot knows about: alert types first, then threat types.
# The order here is the order used in messages and in the settings keyboard.
ALERT_KINDS = {
    # alert_type
    "air_raid": "🚨 Air raid",
    "artillery_shelling": "💥 Artillery shelling",
    "urban_fights": "⚔️ Urban fights",
    "chemical": "☣️ Chemical danger",
    "nuclear": "☢️ Nuclear danger",
    # threats[].threat_type
    "ballistic_missiles": "🚀 Ballistic missiles",
    "cruise_missiles": "🚀 Cruise missiles",
    "unspecified_missiles": "🚀 Missiles (unspecified)",
    "mig31k_departure": "✈️ MiG-31K departure (Kinzhal)",
    "strategic_aircraft_activity": "✈️ Strategic aviation",
    "tactic_aircraft_activity": "✈️ Tactical aviation",
    "drones": "🛸 Drones (UAV)",
    "guided_aerial_bombs": "💣 Guided aerial bombs",
    "air_defense": "🛡 Air defense active",
    "unknown": "❓ Unknown threat",
}

_KIND_ORDER = {kind: i for i, kind in enumerate(ALERT_KINDS)}


def kind_label(kind):
    return ALERT_KINDS.get(kind, f"❓ {kind}")


# Threat groups for the one-line level message, most dangerous first.
# Kinds not listed here (air_raid, air_defense, unknown, new API values)
# fall back to "air raid".
THREAT_GROUPS = [
    ("nuclear", {"nuclear"}),
    ("chemical", {"chemical"}),
    (
        "missile",
        {
            "ballistic_missiles",
            "cruise_missiles",
            "unspecified_missiles",
            "mig31k_departure",
        },
    ),
    ("guided bomb", {"guided_aerial_bombs"}),
    ("aviation", {"strategic_aircraft_activity", "tactic_aircraft_activity"}),
    ("drone", {"drones"}),
    ("artillery", {"artillery_shelling"}),
    ("urban combat", {"urban_fights"}),
]

LEVEL_NAMES = {
    "red": "🔴 Red level",
    "yellow": "🟡 Yellow level",
    "alert": "🚨 Alert",  # alert without alert_level in the API data
}


def threat_summary(kinds):
    """'missile, drone threat' style summary of the given kinds."""
    words = [word for word, group in THREAT_GROUPS if kinds & group]
    return f"{', '.join(words) if words else 'air raid'} threat"


def level_line(level, kinds):
    """One-line message, e.g. '🔴 Red level — missile threat'."""
    return f"{LEVEL_NAMES.get(level, LEVEL_NAMES['alert'])} — {threat_summary(kinds)}"


def sort_kinds(kinds):
    """Sort kinds in ALERT_KINDS order; unknown kinds go last, alphabetically."""
    return sorted(kinds, key=lambda k: (_KIND_ORDER.get(k, len(_KIND_ORDER)), k))


# Persistent client instance for caching and rate limit handling
_client = AsyncClient(token=token)

_LEVEL_RANK = {None: 0, "yellow": 1, "red": 2}


async def get_alerts():
    """Return (active_kinds, alert_level) for CITY, or None if the API failed.

    active_kinds is a set of alert_type and threat_type strings.
    alert_level is "red", "yellow" or None (the highest among the city's alerts).
    """
    try:
        await _client.get_active_alerts()

        # alert_level and threats are not parsed by the library,
        # so we read them from the raw cached response
        raw_alerts = _client.cache.get("alerts/active.json", {}).get("Data", {})
        raw_list = raw_alerts.get("alerts", [])
        city_alerts = [a for a in raw_list if a.get("location_title") == CITY]

        kinds = set()
        level = None
        for alert in city_alerts:
            if alert.get("alert_type"):
                kinds.add(alert["alert_type"])
            for threat in alert.get("threats") or []:
                if threat.get("threat_type"):
                    kinds.add(threat["threat_type"])
            alert_level = alert.get("alert_level")
            if _LEVEL_RANK.get(alert_level, 0) > _LEVEL_RANK.get(level, 0):
                level = alert_level

        return kinds, level

    except Exception as e:  # noqa: BLE001
        logger.error(f"[API ERROR] Failed to check alert: {e}")
        return None
