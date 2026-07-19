import asyncio

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import logging
import string
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from pyrogram import Client, filters
from pyrogram.types import Message

import config
from database import UserManager

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

app = Client(
    "my_account",
    api_id=config.API_ID,
    api_hash=config.API_HASH
)

user_manager = UserManager()

def get_keyboard():
    kb = [
        [KeyboardButton(text="Підписатись"), KeyboardButton(text="Відписатись")],
        [KeyboardButton(text="Розм'ютити"), KeyboardButton(text="Зам'ютити")],
        [KeyboardButton(text="Інфо")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    await message.answer("Головне меню. Оберіть дію на клавіатурі:", reply_markup=get_keyboard())

@dp.message(F.text == "Підписатись")
async def subscribe_action(message: types.Message):
    user_manager.add_user(message.from_user.id)
    logging.info(f"Користувач {message.from_user.id} ПІДПИСАВСЯ.")
    await message.answer("Ви успішно підписалися на сповіщення!", reply_markup=get_keyboard())

@dp.message(F.text == "Відписатись")
async def unsubscribe_action(message: types.Message):
    user_manager.remove_user(message.from_user.id)
    logging.info(f"Користувач {message.from_user.id} ВІДПИСАВСЯ.")
    await message.answer("Ви відписалися від сповіщень.", reply_markup=get_keyboard())

@dp.message(F.text == "Розм'ютити")
async def unmute_action(message: types.Message):
    success = user_manager.unmute_user(message.from_user.id)
    if success:
        logging.info(f"Користувач {message.from_user.id} РОЗМ'ЮТИВСЯ.")
        await message.answer("Сповіщення відновлено! Ви почуєте про наступну загрозу.", reply_markup=get_keyboard())
    else:
        await message.answer("Ви ще не підписані. Натисніть 'Підписатись'.", reply_markup=get_keyboard())

@dp.message(F.text == "Зам'ютити")
async def mute_action(message: types.Message):
    success = user_manager.mute_user(message.from_user.id)
    if success:
        logging.info(f"Користувач {message.from_user.id} ЗАМ'ЮТИВСЯ.")
        await message.answer("Сповіщення тимчасово вимкнено. Ви не будете отримувати тривоги, поки не натиснете 'Розм'ютити' або поки не буде відбою.", reply_markup=get_keyboard())
    else:
        await message.answer("Ви ще не підписані. Натисніть 'Підписатись'.", reply_markup=get_keyboard())

@dp.message(F.text == "Інфо")
async def info_action(message: types.Message):
    info_text = (
        "ℹ️ <b>Інформація про бота</b>\n\n"
        "Цей бот моніторить канали на наявність повідомлень про швидкісні цілі та балістику.\n\n"
        "• <b>Підписатись</b> — отримувати сповіщення\n"
        "• <b>Відписатись</b> — повністю перестати отримувати сповіщення\n"
        "• <b>Зам'ютити</b> — тимчасово вимкнути сповіщення (наприклад, якщо ви вже в укритті)\n"
        "• <b>Розм'ютити</b> — увімкнути сповіщення знову\n\n"
        "<i>При надсиланні тривоги бот м'ютить вас автоматично, щоб не спамити. При відбої — розм'ючує.</i>"
    )
    await message.answer(info_text, parse_mode="HTML", reply_markup=get_keyboard())

@app.on_message(filters.chat(config.CHANNELS_TO_MONITOR))
async def handle_channel_message(client: Client, message: Message):
    text = message.text or message.caption
    if not text:
        return
    
    chat_title = message.chat.title or "Unknown Chat"
    # Щоб не спамити повними текстами, виводимо перші 100 символів
    logging.info(f"[Повідомлення з {chat_title}] {text[:100]}...")
    
    clean_text = text.lower()
    clean_text = clean_text.translate(str.maketrans('', '', string.punctuation))
    
    ignore_words = getattr(config, 'IGNORE_WORDS', [])
    if any(iw.lower() in clean_text for iw in ignore_words):
        return  # Це новина, зведення або повідомлення про наслідки, ігноруємо
    
    # Видаляємо пунктуацію з точних фраз для коректного порівняння з clean_text
    exact_threats = [phrase.translate(str.maketrans('', '', string.punctuation)).lower() for phrase in getattr(config, 'EXACT_THREATS', [])]
    found_words = [phrase for phrase in exact_threats if phrase in clean_text]
    
    # Якщо точних фраз немає, перевіряємо комбінацію: "дія" + "зброя"
    if not found_words:
        weapons = [w for w in getattr(config, 'WEAPONS', []) if w.lower() in clean_text]
        actions = [a for a in getattr(config, 'ACTION_WORDS', []) if a.lower() in clean_text]
        
        # Сумісність зі старим TARGET_WORDS (якщо є)
        legacy_targets = [w for w in getattr(config, 'TARGET_WORDS', []) if w.lower() in clean_text]
        
        if weapons and actions:
            found_words = weapons + actions
        elif legacy_targets and not hasattr(config, 'EXACT_THREATS'):
            found_words = legacy_targets

    clear_words = [word for word in config.CLEAR_WORDS if word.lower() in clean_text]
    
    if clear_words:
        unmuted_ids = user_manager.unmute_all_users()
        for uid in unmuted_ids:
            try:
                await bot.send_message(chat_id=uid, text="Відбій тривоги/Чисто. Ви знову отримуватимете сповіщення про нові загрози.", reply_markup=get_keyboard())
            except Exception as e:
                logging.error(e)
        return  # Зупиняємось, щоб не парсити повідомлення далі
        
    if found_words:
        chat_title = message.chat.title
        chat_name = f"@{message.chat.username}" if message.chat.username else chat_title
        
        timestamp = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d:%m:%Y %H:%M")
        words_str = ", ".join(found_words)
        full_text = message.text or message.caption or ""
        
        alert_text = f"{timestamp}\nWARNING: {words_str}\n\n{chat_name} - {full_text}\n\nВас автоматично зам'ючено від спаму. Натисніть «Розм'ютити» на клавіатурі або дочекайтеся відбою."
        
        print(f"\n{'-'*30}\n{alert_text}\n{'-'*30}\n")
        
        users = user_manager.get_all_users()
        sent_any = False
        
        for user in users:
            # Метод send_alert сам перевіряє, чи не зам'ючений користувач, і м'ютить після відправки
            was_sent = await user.send_alert(bot, alert_text)
            if was_sent:
                sent_any = True
                
        # Зберігаємо базу, якщо хоча б одного користувача було щойно зам'ючено
        if sent_any:
            user_manager.save()

async def main():
    await app.start()
    try:
        await dp.start_polling(bot)
    finally:
        await app.stop()
    
if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
