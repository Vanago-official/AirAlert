import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
import os
import asyncio
from collections import deque

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
import configparser
from alert import get_alert
from database import *
from ai_handler import analyze_message

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

config = configparser.ConfigParser()
config.read("config.cfg")

CHANNELS = [int(x.strip()) for x in config["Settings"]["CHANNELS"].split(",")]
CITY = config["Settings"]["CITY"]

app = Client(
    "balistika_alarm_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH,
)

userbot = Client(
    "@balistika_alarm_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
)

alert_status = False
message_history = deque(maxlen=10)
city_threat_active = False
processed_msg_ids = deque(maxlen=1000)



def status_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Activate"), KeyboardButton("Deactivate")],
            [KeyboardButton("Mute"), KeyboardButton("Unmute")],
            [KeyboardButton("Status"), KeyboardButton("Info")],
        ],
        resize_keyboard=True,
    )

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await add_user(message.chat.id)

    await message.reply_text(
        "Hi! I'm a bot that lets you monitor direct ballistic missile threats to the city of Kyiv.",
        reply_markup=status_keyboard(),
    )

# FETCHING MESSAGES
async def monitor_channels(client, message):
    global alert_status, city_threat_active, message_history, processed_msg_ids

    msg_id_tuple = (message.chat.id, message.id)
    if msg_id_tuple in processed_msg_ids:
        return
    processed_msg_ids.append(msg_id_tuple)

    if message.chat.username:
        source = f"@{message.chat.username}"
    else:
        source = message.chat.title
    
    text = message.text or message.caption
    if not text:
        return

    logging.info(f"[MESSAGE] {source} - {text}")

    message_history.append({"source": source, "text": text})

    if not alert_status:
        return

    history_texts = [msg["text"] for msg in message_history]
    ai_response = await analyze_message(text, history_texts, city_threat_active)

    logging.info(f"[AI] {ai_response}")

    if ai_response == "THREAT":
        city_threat_active = True
        users = await get_active_users()
        await set_all_mutes(1)
        for user_id in users:
            try:
                formatted_message = f"{source}: {text}\n\n__You are automatically muted until the alert is over.__"
                await app.send_message(
                    chat_id=user_id,
                    text=formatted_message,
                    reply_markup=status_keyboard()
                )
            except Exception as ex:
                logging.error(f"[ERROR] {ex}")
    elif ai_response == "CLEAR":
        city_threat_active = False


# MENU BUTTONS
@app.on_message(filters.text & filters.regex("^Activate$"))
async def active_button(client, message):
    await set_user_active(message.chat.id, 1)
    await set_user_mute(message.chat.id, 0)
    await message.reply_text("Bot activated. You will receive threat alerts.")


@app.on_message(filters.text & filters.regex("^Deactivate$"))
async def deactivate_button(client, message):
    await set_user_active(message.chat.id, 0)
    await message.reply_text("Bot deactivated. You will not receive any alerts.")


@app.on_message(filters.text & filters.regex("^Mute$"))
async def mute_button(client, message):
    await set_user_mute(message.chat.id, 1)
    await message.reply_text(
        "Alerts muted. You will not receive notifications until the all-clear signal."
    )


@app.on_message(filters.text & filters.regex("^Unmute$"))
async def unmute_button(client, message):
    await set_user_mute(message.chat.id, 0)
    await message.reply_text("Alerts unmuted. You will receive all notifications.")


@app.on_message(filters.text & filters.regex("^Status$"))
async def status_button(client, message):
    info = await get_user_info(message.chat.id)

    if info is None:
        await message.reply_text(
            "Error: User not found in the database. Please send /start."
        )
        return

    await message.reply_text(
        f"Your status:\nActive: {'+' if info[0] else '-'}\nMuted: {'+' if info[1] else '-'}"
    )


@app.on_message(filters.text & filters.regex("^Info$"))
async def info_button(client, message):
    info_text = (
        "This bot was created as a pet project by @vanago_official."
        "It monitors radar channels in real-time and uses Artificial Intelligence "
        "to filter out spam, providing you with immediate alerts ONLY about direct "
        "ballistic or missile threats to your city."
    )
    await message.reply_text(info_text)



last_message_ids = {}

async def poll_channels():
    logging.info("[STATUS] Started background polling for channels to bypass Telegram restrictions...")
    while True:
        try:
            for chat_id in CHANNELS:
                try:
                    async for msg in userbot.get_chat_history(chat_id, limit=1):
                        if chat_id not in last_message_ids:
                            last_message_ids[chat_id] = msg.id
                        elif msg.id > last_message_ids[chat_id]:
                            last_message_ids[chat_id] = msg.id
                            # Manually trigger the handler
                            logging.info(f"[POLL] Found new message in {chat_id}")
                            await monitor_channels(userbot, msg)
                except Exception as e:
                    pass
        except Exception:
            pass
        await asyncio.sleep(5)

async def main():
    await init_db()
    await app.start()
    await userbot.start()
    logging.info("[STATUS] bot is started. Caching dialogs...")

    try:
        # Примусово провантажуємо всі чати в кеш Pyrogram
        async for _ in userbot.get_dialogs():
            pass
        logging.info("[STATUS] Dialogs cached successfully.")
    except Exception as e:
        logging.warning(f"[STATUS] Could not cache dialogs: {e}")

    asyncio.create_task(poll_channels())


    global alert_status

    try:
        while True:
            is_alert = await get_alert()

            if is_alert and not alert_status:
                alert_status = True
                city_threat_active = False
                logging.info(f"[ALERT] {CITY}")
                
                # Re-analyze recent messages from the buffer
                history_texts = []
                for msg in message_history:
                    history_texts.append(msg["text"])
                    ai_response = await analyze_message(msg["text"], history_texts.copy(), city_threat_active)
                    logging.info(f"[AI BUFFER] {ai_response} for message: {msg['text']}")
                    if ai_response == "THREAT":
                        if not city_threat_active:
                            city_threat_active = True
                            await set_all_mutes(1)
                        users = await get_active_users()
                        for user_id in users:
                            try:
                                formatted_message = f"{msg['source']}: {msg['text']}"
                                await app.send_message(
                                    chat_id=user_id,
                                    text=formatted_message,
                                    reply_markup=status_keyboard()
                                )
                            except Exception as ex:
                                logging.error(f"[ERROR] {ex}")
                    elif ai_response == "CLEAR":
                        city_threat_active = False

            elif not is_alert and alert_status:
                logging.info(f"[ALERT END] {CITY}")
                alert_status = False
                city_threat_active = False
                await set_all_mutes(0)
                message_history.clear()

            await asyncio.sleep(60)

    finally:
        await app.stop()
        await userbot.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("\nBot stoped.")
