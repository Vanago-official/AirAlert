# 🚨 Balistika Alarm Bot

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0%2B-green)
![Gemini AI](https://img.shields.io/badge/AI-Google_Gemini-orange)

**Balistika Alarm Bot** is a smart Telegram bot designed to monitor radar channels in real-time. It uses Artificial Intelligence to analyze messages and instantly warn users about direct ballistic or cruise missile threats to their city.

---

## ✨ Key Features

- 🧠 **AI Analytics (Gemini 3.5 Flash Lite):** The AI filters out informational noise, fundraisers, and general aviation movements, reacting exclusively to real threats.
- 🔄 **Hybrid Context Engine:** The bot "remembers" message history. If the first message was "Ballistics towards the city!", it will instantly react to a follow-up message like "two more targets" because it understands the context of the situation.
- 📡 **Official Alerts Integration:** The bot connects to the official alerts API (`ubilling.net.ua`) and only activates radar analysis when air raid sirens are active in your city.
- 🔕 **Smart Mute:** To prevent spam, the bot automatically mutes users until the all-clear signal after the first warning is sent (users can unmute themselves manually via a button).
- ⚡️ **Userbot Integration:** Powered by Pyrogram, the bot acts as a fully-fledged user, allowing it to read any private or public radar channels and supergroups.

---

## 🛠 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/Vanago-official/BalistikaAlarm.git
cd BalistikaAlarm
```

### 2. Create a virtual environment and install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure the environment
Create a `.env` file in the root of the project and fill it with your credentials:
```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
AI_KEY=your_google_gemini_api_key
```
*(You can obtain your API_ID and API_HASH at [my.telegram.org](https://my.telegram.org))*

### 4. Configure radars and your city
Edit the `config.cfg` file:
```ini
[Settings]
ALERT_API=https://ubilling.net.ua/aerialalerts/
CITY=м. Київ
CHANNELS=-1001223955273, -1001361050199, -1001867382165
```
> **Note:** Enter the exact numerical channel IDs, making sure they include the `-100` prefix.

### 5. First Run
```bash
python main.py
```
During the first launch, the script will ask you to enter your phone number and Telegram confirmation code. This is necessary to authorize the `userbot.session` that will read the radar channels on your behalf.

---

## 🏗 How it Works (Architecture)

1. **Background Monitoring (No Alert):** The userbot silently reads all messages from the radars and buffers the last 10 messages.
2. **Alert Start:** As soon as the API confirms an air raid siren in the city, the bot "wakes up" and sends the message buffer to the AI for analysis.
3. **AI Analysis:** Gemini analyzes the history and the current threat status. If the AI responds with `THREAT`, the bot immediately broadcasts the warning to all active users.
4. **All-Clear:** If the AI responds with `CLEAR` (e.g., "reconnaissance", "clear"), or if the official siren ends — the bot resets the threat status and unmutes all users.

---

## 📜 License
This project was created to protect lives and ensure rapid response to threats. Feel free to use it, but remember: the bot is only an auxiliary tool and does not replace official emergency alert systems. Stay safe! 🇺🇦
