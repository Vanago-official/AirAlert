import os
import httpx
import logging

logger = logging.getLogger(__name__)
import configparser
from dotenv import load_dotenv

load_dotenv()
AI_KEY = os.getenv("AI_KEY")

config = configparser.ConfigParser()
config.read("config.cfg")
CITY = config["Settings"]["CITY"]

SYSTEM_PROMPT = f"""Ти військовий аналітик. Твоя задача — аналізувати ОСТАННЄ повідомлення з радарів і визначати рівень загрози для міста {CITY}.

Тобі буде надано:
1. Поточний статус загрози (СТАТУС ЗАГРОЗИ МІСТУ: АКТИВНА або НЕМАЄ). Якщо АКТИВНА — місто ВЖЕ під атакою або є попередня загроза.
2. Історію останніх повідомлень для розуміння контексту.
3. НОВЕ повідомлення, яке треба проаналізувати.

ПРАВИЛА:
1. Відповідай СУВОРО одним словом: THREAT, SEMITHREAT, IGNORE або CLEAR.
2. ВАЖЛИВО: Оцінюй на загрозу ВИКЛЮЧНО "НОВЕ ПОВІДОМЛЕННЯ". Історія потрібна ТОЛЬКИ для розуміння контексту (наприклад, якщо нове повідомлення це слово "чисто", історія допоможе зрозуміти, що саме чисто). Ніколи не видавай THREAT чи SEMITHREAT, якщо саме НОВЕ повідомлення не є загрозою.
3. Відповідай THREAT, якщо нове повідомлення містить ПРЯМУ БАЛІСТИЧНУ АБО РАКЕТНУ загрозу для {CITY} (або її районів) чи очевидну загальну балістичну загрозу ("Балістика!", "Пуски!"), АБО якщо 'СТАТУС ЗАГРОЗИ МІСТУ' = АКТИВНА і нове повідомлення логічно продовжує РАКЕТНУ/БАЛІСТИЧНУ загрозу для {CITY}.
4. Відповідай SEMITHREAT, якщо для міста {CITY} (або районів) є небезпека, але вона НЕ балістична і НЕ ракетна (наприклад, наближення БПЛА, дронів, "шахедів", "мопедів").
5. Якщо повідомлення вказує на закінчення загрози ("чисто", "дорозвідка", "відбій", "зникла", "впала") — відповідай CLEAR.
6. Назви районів (Оболонь, Троєщина, Печерськ, Дарниця тощо) є частиною міста {CITY}, тому розцінюй загрозу для них як загрозу для міста (THREAT або SEMITHREAT залежно від типу загрози).
7. Передмістя та міста області (Вишгород, Бровари, Вишневе, Ірпінь тощо) НЕ Є містом {CITY}. Ігноруй їх (відповідай IGNORE).
8. Багато повідомлень містять рекламний спам (наприклад "Надіслати новину", "Підписатися", "@username", "ㅤ"). Ігноруй його і аналізуй лише суть.
9. Ігноруй повідомлення про інші міста, збори коштів чи новини (відповідай IGNORE)."""

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
            logger.error(f"[AI ERROR] Gemini API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 logger.error(f"Response data: {e.response.text}")
            return "IGNORE"