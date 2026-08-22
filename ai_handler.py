import os
import httpx
import logging
import configparser
from dotenv import load_dotenv

load_dotenv()
AI_KEY = os.getenv("AI_KEY")

config = configparser.ConfigParser()
config.read("config.cfg")
CITY = config["Settings"]["CITY"]

SYSTEM_PROMPT = f"""Ти військовий аналітик. Твоя задача — аналізувати ОСТАННЄ повідомлення з радарів і визначати, чи несе воно загрозу для міста {CITY}.

Тобі буде надано:
1. Поточний статус загрози (СТАТУС ЗАГРОЗИ МІСТУ: АКТИВНА або НЕМАЄ). Якщо АКТИВНА — місто ВЖЕ під атакою.
2. Історію останніх повідомлень для розуміння контексту.
3. НОВЕ повідомлення, яке треба проаналізувати.

ПРАВИЛА:
1. Відповідай СУВОРО одним словом: THREAT, IGNORE або CLEAR.
2. ВАЖЛИВО: Оцінюй на загрозу ВИКЛЮЧНО "НОВЕ ПОВІДОМЛЕННЯ". Історія потрібна ТОЛЬКИ для розуміння контексту (наприклад, якщо нове повідомлення це слово "чисто", історія допоможе зрозуміти, що саме чисто). Ніколи не видавай THREAT, якщо саме НОВЕ повідомлення не є загрозою (наприклад, збір коштів, реклама, новина).
3. Якщо 'СТАТУС ЗАГРОЗИ МІСТУ' = АКТИВНА, і нове повідомлення (наприклад, "ще цілі", "повернула на нас") логічно продовжує загрозу для {CITY} — відповідай THREAT.
4. Якщо 'СТАТУС ЗАГРОЗИ МІСТУ' = НЕМАЄ, реагуй (THREAT) ЛИШЕ коли в новому повідомленні чітко згадується {CITY} або очевидна загальна балістична загроза (наприклад, "Балістика!", "Пуски!").
5. Якщо повідомлення вказує на закінчення загрози ("чисто", "дорозвідка", "відбій", "зникла", "впала") — відповідай CLEAR.
6. Ігноруй повідомлення про інші міста, збори коштів, рекламу чи новини (відповідай IGNORE)."""

async def analyze_message(text: str, history: list, city_threat: bool) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={AI_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    history_text = "\n".join([f"- {msg}" for msg in history[:-1]]) if len(history) > 1 else "Немає"
    
    user_prompt = f"СТАТУС ЗАГРОЗИ МІСТУ ({CITY}): {'АКТИВНА' if city_threat else 'НЕМАЄ'}\n"
    user_prompt += f"ІСТОРІЯ ПОВІДОМЛЕНЬ:\n{history_text}\n\n"
    user_prompt += f"НОВЕ ПОВІДОМЛЕННЯ:\n{text}\n"
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [{
            "parts": [{"text": user_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.0
        }
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Дістаємо текст відповіді зі специфічної структури Gemini
            answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return answer
            
        except Exception as e:
            logging.error(f"[AI ERROR] Gemini API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 logging.error(f"Response data: {e.response.text}")
            return "IGNORE"