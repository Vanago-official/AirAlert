import asyncio

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import logging
import string
import re
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp

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
        [KeyboardButton(text="Статус"), KeyboardButton(text="Інфо")]
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

@dp.message(F.text == "Статус")
async def status_action(message: types.Message):
    user = user_manager.get_user(message.from_user.id)
    if not user:
        await message.answer("Ви не підписані на сповіщення. Натисніть 'Підписатись'.", reply_markup=get_keyboard())
    elif user.muted:
        await message.answer("Ваш статус: ЗАМ'ЮЧЕНО\nВи не будете отримувати тривоги до наступного відбою або поки не натиснете 'Розм'ютити'.", reply_markup=get_keyboard())
    else:
        await message.answer("Ваш статус: АКТИВНО\nВи отримуєте всі сповіщення про нові загрози.", reply_markup=get_keyboard())

@dp.message(F.text == "Інфо")
async def info_action(message: types.Message):
    info_text = (
        "ℹ️ <b>Інформація про бота</b>\n\n"
        "Цей бот моніторить канали на наявність повідомлень про швидкісні цілі та балістику.\n\n"
        "• <b>Підписатись</b> — отримувати сповіщення\n"
        "• <b>Відписатись</b> — повністю пета ну рестати отримувати сповіщення\n"
        "• <b>Зам'ютити</b> — тимчасово вимкнути сповіщення (наприклад, якщо ви вже в укритті)\n"
        "• <b>Розм'ютити</b> — увімкнути сповіщення знову\n"
        "• <b>Статус</b> — перевірити, чи увімкнені у вас зараз сповіщення\n\n"
        "<i>При надсиланні тривоги бот м'ютить вас автоматично, щоб не спамити. При відбої — розм'ючує.</i>"
    )
    await message.answer(info_text, parse_mode="HTML", reply_markup=get_keyboard())

@app.on_message(filters.chat(config.CHANNELS_TO_MONITOR))
@app.on_edited_message(filters.chat(config.CHANNELS_TO_MONITOR))
async def handle_channel_message(client: Client, message: Message):
    text = message.text or message.caption
    if not text:
        return
        
    chat_title = message.chat.title or "Unknown Chat"
    logging.info(f"[Повідомлення з {chat_title}] {text[:100]}...")
    
    clean_text = text.lower()
    
    # 1. ЖОРСТКИЙ ФІЛЬТР: якщо це дрони/КАБи або інше місто - одразу ігноруємо
    ignore_words = ["бпла", "шахед", "дрон", "мопед", "каб", "каби", "харків", "сумщин", "одес", "дніпр", "запоріж", "полтав", "херсон", "миколаїв", "чернігів"]
    if any(word in clean_text for word in ignore_words) and "київ" not in clean_text:
        logging.info("[ФІЛЬТР] Пропущено (БпЛА/КАБ або інше місто)")
        return
    
    prompt = f"""Ти — система аналізу повітряних тривог для міста КИЇВ. Твоє завдання — визначити тип повідомлення.
Відповідай ЗАВЖДИ лише одним словом: CLEAR, THREAT або IGNORE. Жодних інших слів.

Правила:
- CLEAR: якщо пишуть "відбій", "чисто", "дорозвідка", "небо чисте".
- THREAT: ТІЛЬКИ якщо є пряма загроза РАКЕТ або БАЛІСТИКИ (ракети, балістика, кинджали, іскандери, швидкісні цілі, пуск, пуски) І ця загроза стосується КИЄВА або є загальною.
- IGNORE: ігноруй будь-які згадки про шахеди, БпЛА, дрони або КАБи. Ігноруй попередження типу "загроза застосування балістичного озброєння" чи "активність авіації", якщо НЕМАЄ інформації про реальний пуск. Ігноруй ракети, якщо чітко вказано, що вони летять в ІНШІ міста (не на Київ). Ігноруй новини та звіти ППО.

Приклади:
Повідомлення: "Відбій загрози по областях"
Відповідь: CLEAR

Повідомлення: "Увага! Швидкісна ціль на Київ!"
Відповідь: THREAT

Повідомлення: "Пуски ракет з тактичної авіації!"
Відповідь: THREAT

Повідомлення: "Загроза застосування балістичного озброєння з півдня!"
Відповідь: IGNORE

Повідомлення: "Активність ворожої тактичної авіації! Загроза застосування авіаційних засобів ураження!"
Відповідь: IGNORE

Повідомлення: "Шахеди летять на Київ"
Відповідь: IGNORE

Повідомлення: "Ракета на Харків"
Відповідь: IGNORE

Повідомлення: "КАБи на Сумщину"
Відповідь: IGNORE

Повідомлення: "{text}"
Відповідь:"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {getattr(config, 'GROQ_API_KEY', '')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_decision = data["choices"][0]["message"]["content"].strip().upper()
                else:
                    error_text = await response.text()
                    logging.error(f"Помилка Groq API: {response.status} - Деталі: {error_text}")
                    return
    except Exception as e:
        logging.error(f"Не вдалося підключитися до Groq API: {e}")
        return

    logging.info(f"[AI Рішення] {ai_decision}")

    if "CLEAR" in ai_decision:
        unmuted_ids = user_manager.unmute_all_users()
        for uid in unmuted_ids:
            try:
                await bot.send_message(chat_id=uid, text="Чисто. Ви знову отримуватимете сповіщення про нові загрози.", reply_markup=get_keyboard())
            except Exception as e:
                logging.error(e)
        return

    elif "THREAT" in ai_decision:
        chat_name = f"@{message.chat.username}" if message.chat.username else chat_title
        full_text = message.text or message.caption or ""
        
        alert_text = f"🚨 УВАГА!\n\n{chat_name} - {full_text}\n\nВас автоматично зам'ючено від спаму. Натисніть «Розм'ютити» на клавіатурі або дочекайтеся відбою."
        
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
