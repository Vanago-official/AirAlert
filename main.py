import asyncio

from database import set_ai_clear_sending, set_clear_sending

# Fix for Pyrogram: it tries to get the event loop on import
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import configparser
import logging
from os import getenv

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from ai import ThreatAnalyzer
from alarm import get_alert
from database import (
    add_user,
    get_active_users,
    get_ai_clear_users,
    get_muted_users,
    get_user_info,
    init_db,
    set_all_mutes,
    set_user_active,
    set_user_mute,
)
from userbot import ChannelMonitor

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Config and ENV
BOT_TOKEN = getenv("BOT_TOKEN")
API_ID = getenv("API_ID")
API_HASH = getenv("API_HASH")

config = configparser.ConfigParser()
config.read("config.cfg")
CHANNELS = [int(ch.strip()) for ch in config["Settings"]["CHANNELS"].split(",")]

alert_status = False
current_alert_level = None  # None, "yellow", "red"
current_threat_types = []  # ["drones", "ballistic_missiles", ...]
current_alert_type = None  # "air_raid", "artillery_shelling", etc.

# Is there an active threat from the userbot (Gemini channel analysis)
userbot_threat_active = False

MISSILE_THREATS = {
    "ballistic_missiles",
    "cruise_missiles",
    "unspecified_missiles",
}

ALERT_TYPE_LABELS = {
    "air_raid": "Air Raid",
    "artillery_shelling": "Artillery Shelling",
    "urban_fights": "Urban Fights",
    "chemical": "Chemical Danger",
    "nuclear": "Nuclear Danger",
}

THREAT_LABELS = {
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

LEVEL_LABELS = {
    "red": "🔴 Red (missile/massive drone threat)",
    "yellow": "🟡 Yellow (drone threat)",
}

bot = Bot(BOT_TOKEN)  # pyright: ignore[reportArgumentType]
dp = Dispatcher()

# Instantiate analyzer and monitor
analyzer = ThreatAnalyzer(model="gemini-2.5-flash")
channel_monitor = ChannelMonitor(
    api_id=API_ID,  # pyright: ignore[reportArgumentType]
    api_hash=API_HASH,  # pyright: ignore[reportArgumentType]
    channels=CHANNELS,
    analyzer=analyzer,
    poll_interval=10,
)


async def send_danger_message():
    global userbot_threat_active
    userbot_threat_active = True

    users = await get_active_users()
    await set_all_mutes(1)

    for user in users:
        try:
            await bot.send_message(chat_id=user, text="🔴 Danger!")
            await asyncio.sleep(0.05)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[BOT ERROR] Failed to send message to user {user}: {e}")


async def send_clear_message(text: str = "🟢 Clear."):
    global userbot_threat_active
    userbot_threat_active = False

    users = await get_muted_users()
    await set_all_mutes(0)

    for user in users:
        try:
            await bot.send_message(chat_id=user, text=text)
            await asyncio.sleep(0.05)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[BOT ERROR] Failed to send message to user {user}: {e}")


async def send_ai_clear_message():
    global userbot_threat_active
    userbot_threat_active = False

    # Беремо юзерів, які зам'ючені і хочуть отримувати ШІ-відбої
    users = await get_ai_clear_users()
    # НЕ розм'ючуємо нікого (вони чекають на офіційний відбій)

    for user in users:
        try:
            await bot.send_message(chat_id=user, text="🟢 Probably clear.")
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(
                f"[BOT ERROR] Failed to send AI clear message to user {user}: {e}"
            )


# --- Callbacks для юзер-бота (Gemini аналіз каналів) ---


async def on_userbot_threat():
    """Викликається юзер-ботом, коли Gemini визначив THREAT."""
    global userbot_threat_active
    if not userbot_threat_active:
        logger.info("[USERBOT → BOT] Gemini detected THREAT! Sending alerts...")
        await send_danger_message()


async def on_userbot_clear():
    """Викликається юзер-ботом, коли Gemini визначив CLEAR."""
    global userbot_threat_active
    if userbot_threat_active:
        logger.info("[USERBOT → BOT] Gemini detected CLEAR. Sending AI clear...")
        await send_ai_clear_message()


# Register callbacks
channel_monitor.on_threat(on_userbot_threat)
channel_monitor.on_clear(on_userbot_clear)

replyKeyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔔 Unmute"),
            KeyboardButton(text="🔕 Mute"),
        ],
        [
            KeyboardButton(text="📊 Status"),
            KeyboardButton(text="ℹ️ Info"),
        ],
        [KeyboardButton(text="⚙️ Settings")],
    ],
    resize_keyboard=True,
)


@dp.message(CommandStart())
async def command_start_handler(message):
    await add_user(message.from_user.id)

    await message.answer(
        "👋 Hi! I monitor direct missile threats to Kyiv.\n\nUse the buttons below to control the bot:",
        reply_markup=replyKeyboard,
    )


# MENU BUTTONS
@dp.message(F.text.regexp(r"^🔕 Mute$"))
async def mute_button(message):
    await set_user_mute(message.from_user.id, 1)
    await message.answer("🔕 Alerts muted until all-clear.", reply_markup=replyKeyboard)


@dp.message(F.text.regexp(r"^🔔 Unmute$"))
async def unmute_button(message):
    await set_user_mute(message.from_user.id, 0)
    await message.answer("🔔 Alerts unmuted.", reply_markup=replyKeyboard)


@dp.message(F.text.regexp(r"^📊 Status$"))
async def status_button(message):
    info = await get_user_info(message.from_user.id)

    if info is None:
        await message.answer("⚠️ User not found. Send /start to register.")
        return

    if current_alert_level:
        status_icon = "🔴" if current_alert_level == "red" else "🟡"
        level_text = LEVEL_LABELS.get(
            current_alert_level, f"{status_icon} {current_alert_level.capitalize()}"
        )
        status_lines = [f"🚨 *Air Alert:* {status_icon} {level_text}"]

        if current_threat_types:
            threat_texts = [THREAT_LABELS.get(t, t) for t in current_threat_types]
            status_lines.append(f"🎯 *Threat Type:* {', '.join(threat_texts)}")  # pyright: ignore[reportArgumentType, reportCallIssue]
        if current_alert_type and current_alert_type != "air_raid":
            type_text = ALERT_TYPE_LABELS.get(current_alert_type, current_alert_type)
            status_lines.append(f"📢 *Alert Type:* {type_text}")

        alert_section = "\n".join(status_lines)
    else:
        alert_section = "🚨 *Air Alert:* 🟢 Inactive"

    # Додаємо статус Gemini-аналізу каналів
    gemini_status = "🔴 Active threat" if userbot_threat_active else "🟢 No threat"

    await message.answer(
        f"📊 *Current Status:*\n\n"
        f"{alert_section}\n"
        f"🤖 *Channel AI:* {gemini_status}\n\n"
        f"🟢 *Active:* {'Yes' if info[0] else 'No'}\n"
        f"🔕 *Muted:* {'Yes' if info[1] else 'No'}\n"
        f"📩 *Send Clear:* {'Yes' if info[2] == 1 else 'No'}\n"
        f"🧠 *Send AI Clear:* {'Yes' if info[3] == 1 else 'No'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=replyKeyboard,
    )


@dp.message(F.text.regexp(r"^ℹ️ Info$"))
async def info_button(message):
    info_text = (
        "Created by @vanago\\_official\\.\n\n"
        r"Monitors official air alert data in real\-time and sends instant notifications "
        "about direct missile threats to Kyiv\\.\n\n"
        "🔘 *Buttons:*\n\n"
        "🟢 *Activate* — activates the bot\\. You will receive alerts about missile threats\\.\n"
        "🛑 *Deactivate* — deactivates the bot\\. All alerts are disabled\\.\n"
        "🔔 *Unmute* — unmutes alerts so you receive notifications again\\.\n"
        "🔕 *Mute* — mutes alerts until the current threat ends \\(all\\-clear\\)\\.\n"
        "📊 *Status* — shows the current air alert status and your settings\\.\n"
        r"ℹ️ *Info* — shows this information message\."
    )
    await message.answer(
        info_text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=replyKeyboard
    )


@dp.message(F.text.regexp(r"^⚙️ Settings$"))
async def settings(message):
    info = await get_user_info(message.from_user.id)
    if not info:
        return

    btn_text = "🟢 Send clear" if info[2] == 1 else "🔴 Don't send clear"
    btn_ai_text = "🟢 Send AI clear" if info[3] == 1 else "🔴 Don't send AI clear"

    SettingsKeyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🟢 Activate"),
                KeyboardButton(text="🛑 Deactivate"),
            ],
            [
                KeyboardButton(text=btn_text),
                KeyboardButton(text=btn_ai_text),
            ],
            [KeyboardButton(text="🔙 Back")],
        ],
        resize_keyboard=True,
    )

    SETTINGS_REPLIES = {
        "⚙️ Settings": "⚙️ Settings",
        "🟢 Activate": "🟢 Bot activated. Alerts enabled.",
        "🛑 Deactivate": "🛑 Bot deactivated. Alerts disabled.",
        "🟢 Send clear": "🔴 Clear messages disabled. You won't receive clear messages.",
        "🔴 Don't send clear": "🟢 Clear messages enabled. You will receive clear messages.",
        "🟢 Send AI clear": "🔴 AI clear messages disabled. You won't receive AI clear messages.",
        "🔴 Don't send AI clear": "🟢 AI clear messages enabled. You will receive AI clear messages.",
    }

    answ = SETTINGS_REPLIES.get(message.text)
    if answ:
        await message.answer(answ, reply_markup=SettingsKeyboard)


@dp.message(F.text.regexp(r"^🟢 Activate$"))
async def active_button(message):
    await set_user_active(message.from_user.id, 1)
    await set_user_mute(message.from_user.id, 0)
    await settings(message)


@dp.message(F.text.regexp(r"^🛑 Deactivate$"))
async def deactivate_button(message):
    await set_user_active(message.from_user.id, 0)
    await settings(message)


@dp.message(F.text.regexp(r"^🟢 Send clear$"))
async def disable_clear(message):
    await set_clear_sending(message.from_user.id, 0)
    await settings(message)


@dp.message(F.text.regexp(r"^🔴 Don't send clear$"))
async def enable_clear(message):
    await set_clear_sending(message.from_user.id, 1)
    await settings(message)


@dp.message(F.text.regexp(r"^🟢 Send AI clear$"))
async def disable_ai_clear(message):

    await set_ai_clear_sending(message.from_user.id, 0)
    await settings(message)


@dp.message(F.text.regexp(r"^🔴 Don't send AI clear$"))
async def enable_ai_clear(message):
    await set_ai_clear_sending(message.from_user.id, 1)
    await settings(message)


@dp.message(F.text.regexp(r"^🔙 Back$"))
async def back_to_main(message):
    await message.answer("Main menu:", reply_markup=replyKeyboard)


async def alert_loop():
    global alert_status, current_alert_level, current_threat_types, current_alert_type
    while True:
        try:
            is_alert, threat_types, alert_type = await get_alert()
            has_missile_threat = any(t in MISSILE_THREATS for t in threat_types)
            is_missile_danger = is_alert == "red" and has_missile_threat

            logger.info(
                f"[ALERT] Level: {is_alert} | Type: {alert_type} | Threats: {threat_types} | Danger: {is_missile_danger}"
            )

            # Update current state for status display
            current_alert_level = is_alert if is_alert else None
            current_threat_types = threat_types
            current_alert_type = alert_type

            # New missile danger alert detected
            if is_missile_danger and not alert_status:
                alert_status = True
                await channel_monitor.set_listening(
                    True
                )  # Активуємо аналіз каналів через Gemini
                await send_danger_message()

            # Missile danger ended
            elif not is_missile_danger and alert_status:
                alert_status = False
                await channel_monitor.set_listening(False)  # Вимикаємо аналіз каналів
                await send_clear_message()

        except Exception as e:  # noqa: BLE001
            logger.error(f"[ALERT LOOP ERROR]: {e}")

        await asyncio.sleep(10)


@dp.startup()
async def on_startup():
    await init_db()

    # Запускаємо юзер-бота (Pyrogram)
    await channel_monitor.start()

    # Запускаємо цикл перевірки тривог (API)
    asyncio.create_task(alert_loop())

    logger.info("[STATUS] Bot and userbot started.")


@dp.shutdown()
async def on_shutdown():
    await channel_monitor.stop()
    logger.info("[STATUS] Bot and userbot stopped.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
