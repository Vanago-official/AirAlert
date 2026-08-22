import logging
import httpx
import configparser

config = configparser.ConfigParser()
config.read("config.cfg")

ALERT_API = config["Settings"]["ALERT_API"]
CITY = config["Settings"]["CITY"]

async def get_alert():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(ALERT_API)
            data = response.json()

            if data["states"][CITY]["alertnow"]:
                return True
            
            return False
    except Exception as e:
        logging.error(f"[API ERROR] Не вдалося перевірити тривогу: {e}")
        return False

