import asyncio
import logging
from html import escape
from os import getenv

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from alarm import (
    ALERT_KINDS,
    CITY,
    LEVEL_TOGGLES,
    get_alerts,
    kind_label,
    level_key,
    level_line,
    sort_kinds,
)
from database import (
    add_user,
    apply_auto_mute,
    get_disabled_kinds,
    get_recipients,
    get_user_info,
    init_db,
    set_all_kinds_enabled,
    set_all_mutes,
    set_auto_mute,
    set_clear_sending,
    set_kind_enabled,
    set_user_active,
    set_user_mute,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Config and ENV
BOT_TOKEN = getenv("BOT_TOKEN")

active_kinds = set()  # alert_type and threat_type values active right now
current_level = None  # None, "yellow", "red", "alert" (active without alert_level)
episode_kinds = set()  # every kind seen since the alert started, for the all-clear
episode_levels = set()  # every level seen since the alert started, for the all-clear

ALL_CLEAR_TEXT = "🟢 All clear"

# Everything a user can switch on/off: levels first, then alert kinds
TOGGLES = {**LEVEL_TOGGLES, **ALERT_KINDS}

bot = Bot(BOT_TOKEN)  # pyright: ignore[reportArgumentType]
dp = Dispatcher()


def kinds_list(kinds):
    return "\n".join(f"• {kind_label(k)}" for k in sort_kinds(kinds))


async def send_to(user_id, text):
    try:
        await bot.send_message(chat_id=user_id, text=text)
        await asyncio.sleep(0.05)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"[BOT ERROR] Failed to send message to user {user_id}: {e}")
        return False


async def send_level(level, kinds):
    """One line about the new level, built from the kinds each user has enabled."""
    sent = []
    for user_id, disabled in await get_recipients():
        if level_key(level) in disabled:
            continue
        user_kinds = kinds - disabled
        if user_kinds and await send_to(user_id, level_line(level, user_kinds)):
            sent.append(user_id)
    # Auto-mute mode: after the first alert, stay silent until the all-clear
    await apply_auto_mute(sent)


async def send_all_clear(kinds, levels):
    """All-clear for users who had at least one of the episode's kinds and levels enabled."""
    level_keys = {level_key(level) for level in levels}
    # Muted users get the all-clear too, then their mute is lifted
    for user_id, disabled in await get_recipients(include_muted=True, require_clear=True):
        if kinds - disabled and level_keys - disabled:
            await send_to(user_id, ALL_CLEAR_TEXT)


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
        f"👋 Hi! I'm AirAlert. I monitor alerts in {CITY} "
        "and tell you when the alert level changes.\n\n"
        "Choose which alerts you want in ⚙️ Settings → 🎛 Alert types.\n\n"
        "Use the buttons below to control the bot:",
        reply_markup=replyKeyboard,
    )


# MENU BUTTONS
@dp.message(F.text.regexp(r"^🔕 Mute$"))
async def mute_button(message):
    await set_user_mute(message.from_user.id, 1)
    await message.answer(
        "🔕 Alerts muted until all alerts end.", reply_markup=replyKeyboard
    )


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

    disabled = await get_disabled_kinds(message.from_user.id)
    enabled_count = len(set(ALERT_KINDS) - disabled)
    enabled_levels = ", ".join(
        label for key, label in LEVEL_TOGGLES.items() if key not in disabled
    ) or "None"

    if active_kinds:
        alert_section = (
            f"🚨 <b>Alerts in {escape(CITY)}:</b> {escape(level_line(current_level, active_kinds))}\n"
            f"{kinds_list(active_kinds)}"
        )
    else:
        alert_section = f"🚨 <b>Alerts in {escape(CITY)}:</b> 🟢 None"

    await message.answer(
        f"📊 <b>Current Status:</b>\n\n"
        f"{alert_section}\n\n"
        f"🟢 <b>Active:</b> {'Yes' if info[0] else 'No'}\n"
        f"🔕 <b>Muted:</b> {'Yes' if info[1] else 'No'}\n"
        f"📩 <b>Send Clear:</b> {'Yes' if info[2] == 1 else 'No'}\n"
        f"🔕 <b>Auto-mute:</b> {'On' if info[3] == 1 else 'Off'}\n"
        f"🎚 <b>Levels on:</b> {enabled_levels}\n"
        f"🎛 <b>Alert types on:</b> {enabled_count}/{len(ALERT_KINDS)}",
        parse_mode=ParseMode.HTML,
        reply_markup=replyKeyboard,
    )


@dp.message(F.text.regexp(r"^ℹ️ Info$"))
async def info_button(message):
    info_text = (
        "🚨 <b>AirAlert</b>\n"
        "Created by @vanago_official.\n\n"
        f"Monitors official alert data for {escape(CITY)} in real-time and sends "
        "one line when the alert level changes, e.g. "
        "«🔴 Red level — missile threat», and «🟢 All clear» when it ends.\n\n"
        "🔘 <b>Buttons:</b>\n\n"
        "🔔 <b>Unmute</b> — receive notifications again.\n"
        "🔕 <b>Mute</b> — mute notifications until all alerts end.\n"
        "📊 <b>Status</b> — current alerts and your settings.\n"
        "⚙️ <b>Settings</b> — activate/deactivate the bot, toggle end-of-alert "
        "messages, auto-mute (silence everything after the first alert until "
        "the all-clear), choose alert levels and types.\n"
        "ℹ️ <b>Info</b> — this message."
    )
    await message.answer(
        info_text, parse_mode=ParseMode.HTML, reply_markup=replyKeyboard
    )


@dp.message(F.text.regexp(r"^⚙️ Settings$"))
async def settings(message):
    info = await get_user_info(message.from_user.id)
    if not info:
        return

    btn_text = "🟢 Send clear" if info[2] == 1 else "🔴 Don't send clear"
    auto_mute_text = "🔕 Auto-mute: ON" if info[3] == 1 else "🔔 Auto-mute: OFF"

    SettingsKeyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🟢 Activate"),
                KeyboardButton(text="🛑 Deactivate"),
            ],
            [KeyboardButton(text=btn_text)],
            [KeyboardButton(text=auto_mute_text)],
            [KeyboardButton(text="🎛 Alert types")],
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
        "🔕 Auto-mute: ON": "🔔 Auto-mute disabled. You will receive every alert.",
        "🔔 Auto-mute: OFF": "🔕 Auto-mute enabled. After the first alert, everything is muted until the all-clear.",
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


@dp.message(F.text.regexp(r"^🔕 Auto-mute: ON$"))
async def disable_auto_mute(message):
    await set_auto_mute(message.from_user.id, 0)
    await settings(message)


@dp.message(F.text.regexp(r"^🔔 Auto-mute: OFF$"))
async def enable_auto_mute(message):
    await set_auto_mute(message.from_user.id, 1)
    await settings(message)


# LEVEL AND ALERT TYPE TOGGLES (inline keyboard)
def toggle_button(key, disabled):
    return InlineKeyboardButton(
        text=f"{'❌' if key in disabled else '✅'} {TOGGLES[key]}",
        callback_data=f"kind:{key}",
    )


def alert_types_keyboard(disabled):
    # Levels on the first row, alert types two per row below
    rows = [[toggle_button(key, disabled) for key in LEVEL_TOGGLES]]
    buttons = [toggle_button(kind, disabled) for kind in ALERT_KINDS]
    rows += [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append(
        [
            InlineKeyboardButton(text="✅ Enable all", callback_data="kinds:1"),
            InlineKeyboardButton(text="❌ Disable all", callback_data="kinds:0"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(F.text.regexp(r"^🎛 Alert types$"))
async def alert_types_button(message):
    disabled = await get_disabled_kinds(message.from_user.id)
    await message.answer(
        "🎛 Tap an alert level (first row) or alert type to turn it on (✅) or off (❌):",
        reply_markup=alert_types_keyboard(disabled),
    )


@dp.callback_query(F.data.startswith("kind:"))
async def toggle_kind(callback: CallbackQuery):
    kind = callback.data.split(":", 1)[1]  # pyright: ignore[reportOptionalMemberAccess]
    if kind not in TOGGLES:
        await callback.answer()
        return

    user_id = callback.from_user.id
    disabled = await get_disabled_kinds(user_id)
    enable = kind in disabled
    await set_kind_enabled(user_id, kind, enable)
    disabled.symmetric_difference_update({kind})

    await callback.message.edit_reply_markup(  # pyright: ignore[reportOptionalMemberAccess]
        reply_markup=alert_types_keyboard(disabled)
    )
    await callback.answer(f"{TOGGLES[kind]}: {'on' if enable else 'off'}")


@dp.callback_query(F.data.startswith("kinds:"))
async def toggle_all_kinds(callback: CallbackQuery):
    enable = callback.data == "kinds:1"
    user_id = callback.from_user.id
    old_disabled = await get_disabled_kinds(user_id)
    await set_all_kinds_enabled(user_id, TOGGLES, enable)
    disabled = set() if enable else set(TOGGLES)

    if disabled != old_disabled:
        await callback.message.edit_reply_markup(  # pyright: ignore[reportOptionalMemberAccess]
            reply_markup=alert_types_keyboard(disabled)
        )
    await callback.answer("Everything on" if enable else "Everything off")


@dp.message(F.text.regexp(r"^🔙 Back$"))
async def back_to_main(message):
    await message.answer("Main menu:", reply_markup=replyKeyboard)


async def alert_loop():
    global active_kinds, current_level, episode_kinds, episode_levels
    while True:
        try:
            result = await get_alerts()
            if result is not None:
                kinds, api_level = result
                level = (api_level or "alert") if kinds else None
                previous_level = current_level

                logger.info(
                    f"[ALERT] Level: {level} | Active: {sorted(kinds)} | "
                    f"Previous level: {previous_level}"
                )

                active_kinds = kinds
                current_level = level
                episode_kinds |= kinds
                if level:
                    episode_levels.add(level)

                # Notify only when the level changes; threat changes alone are silent
                if level != previous_level:
                    if level:
                        await send_level(level, kinds)
                    else:
                        await send_all_clear(episode_kinds, episode_levels)
                        episode_kinds = set()
                        episode_levels = set()
                        await set_all_mutes(0)

        except Exception as e:  # noqa: BLE001
            logger.error(f"[ALERT LOOP ERROR]: {e}")

        await asyncio.sleep(10)


@dp.startup()
async def on_startup():
    await init_db()

    # Запускаємо цикл перевірки тривог (API)
    asyncio.create_task(alert_loop())

    logger.info("[STATUS] AirAlert started.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
