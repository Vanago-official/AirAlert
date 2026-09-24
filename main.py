import asyncio
import logging
from os import getenv

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from alarm import get_alert
from database import (
    add_user,
    get_active_users,
    get_muted_users,
    get_user_info,
    init_db,
    set_all_mutes,
    set_user_active,
    set_user_mute,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = getenv("BOT_TOKEN")

alert_status = False
current_alert_level = None   # None, "yellow", "red"
current_threat_types = []    # ["drones", "ballistic_missiles", ...]
current_alert_type = None    # "air_raid", "artillery_shelling", etc.

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
    "red": "🔴 Red (missile threat)",
    "yellow": "🟡 Yellow (drone threat)",
}

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

replyKeyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="✅ Activate"),
            KeyboardButton(text="🛑 Deactivate"),
        ],
        [
            KeyboardButton(text="🔕 Mute"),
            KeyboardButton(text="🔔 Unmute"),
        ],
        [
            KeyboardButton(text="📊 Status"),
            KeyboardButton(text="ℹ️ Info"),
        ],
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
@dp.message(F.text.regexp(r"^✅ Activate$"))
async def active_button(message):
    await set_user_active(message.from_user.id, 1)
    await set_user_mute(message.from_user.id, 0)
    await message.answer("✅ Bot activated. Alerts enabled.", reply_markup=replyKeyboard)


@dp.message(F.text.regexp(r"^🛑 Deactivate$"))
async def deactivate_button(message):
    await set_user_active(message.from_user.id, 0)
    await message.answer("🛑 Bot deactivated. Alerts disabled.", reply_markup=replyKeyboard)


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
        status_lines = [
            f"🚨 *Air Alert:* {status_icon} Active",
            f"⚠️ *Level:* {level_text}",
        ]
        if current_threat_types:
            threat_texts = [
                THREAT_LABELS.get(t, t) for t in current_threat_types
            ]
            status_lines.append(f"🎯 *Threat Type:* {', '.join(threat_texts)}")
        if current_alert_type and current_alert_type != "air_raid":
            type_text = ALERT_TYPE_LABELS.get(
                current_alert_type, current_alert_type
            )
            status_lines.append(f"📢 *Alert Type:* {type_text}")

        alert_section = "\n".join(status_lines)
    else:
        alert_section = "🚨 *Air Alert:* 🟢 Inactive"

    await message.answer(
        f"📊 *Current Status:*\n\n"
        f"{alert_section}\n\n"
        f"✅ *Active:* {'Yes' if info[0] else 'No'}\n"
        f"🔕 *Muted:* {'Yes' if info[1] else 'No'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=replyKeyboard,
    )


@dp.message(F.text.regexp(r"^ℹ️ Info$"))
async def info_button(message):
    info_text = (
        "Created by @vanago_official.\n\n"
        "Monitors official air alert data in real-time and sends instant notifications "
        "about direct missile threats to Kyiv."
    )
    await message.answer(info_text, reply_markup=replyKeyboard)


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
                users = await get_active_users()
                await set_all_mutes(1)

                for user in users:
                    try:
                        await bot.send_message(chat_id=user, text="🔴 Danger!")
                        await asyncio.sleep(0.05)
                    except Exception as e:  # noqa: BLE001
                        logger.error(
                            f"[BOT ERROR] Failed to send message to user {user}: {e}"
                        )

            # Missile danger ended
            elif not is_missile_danger and alert_status:
                alert_status = False
                users = await get_muted_users()
                await set_all_mutes(0)

                for user in users:
                    try:
                        await bot.send_message(chat_id=user, text="🟢 Clear.")
                        await asyncio.sleep(0.05)
                    except Exception as e:  # noqa: BLE001
                        logger.error(
                            f"[BOT ERROR] Failed to send message to user {user}: {e}"
                        )

        except Exception as e:  # noqa: BLE001
            logger.error(f"[ALERT LOOP ERROR]: {e}")

        await asyncio.sleep(10)


@dp.startup()
async def on_startup():
    await init_db()
    asyncio.create_task(alert_loop())
    logger.info("[STATUS] Bot started.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
