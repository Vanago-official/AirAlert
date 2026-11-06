# 🚨 AirAlert

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

**AirAlert** is a Telegram bot that monitors the official Ukrainian alert API and notifies subscribed users with one line whenever the alert level in their city changes, e.g. `🔴 Red level — missile threat`.

---

## ✨ Features

- 🚨 **Any Alert:** Polls the [alerts.in.ua](https://alerts.in.ua/) API every 10 seconds and detects every alert type (air raid, artillery, urban fights, chemical, nuclear) and every threat (missiles, drones, aviation, guided bombs, etc.).
- 📨 **One-Line Messages:** The bot sends a message only when the alert level changes: `<level> — <threat>`.
- 🎛 **Per-Level and Per-Type Toggles:** Every alert level (red, yellow, no level) and every alert type can be turned on or off in Settings → 🎛 Alert types.
- 🔕 **Mute:** Mute notifications until all alerts end. You still get the final all-clear.
- 🔕 **Auto-mute mode:** Optional setting. After the first alert message you are muted automatically until the all-clear.
- ⚙️ **Clear Messages:** Opt in or out of end-of-alert messages.
- 📊 **Status Dashboard:** Shows active alerts, alert level and your settings.
- 💾 **Persistent Storage:** SQLite via `aiosqlite`. Schema changes are applied automatically on startup.

---

## 🏗 Architecture

```text
main.py        — Bot entry point, handlers, alert broadcast loop
alarm.py       — API client for alerts.in.ua, list of alert types
database.py    — SQLite operations (users, mute, active, clear, disabled alert types)
config.cfg     — City configuration
.env           — Tokens and API keys (not committed)
```

**How the alert loop works:**

1. The bot queries the alerts API every 10 seconds and collects all `alert_type` and `threat_type` values for the city.
2. **Level changed** (none, yellow, red): active, unmuted users get one line built from the types they have enabled. Threat changes at the same level send nothing. Users who turned that level off get nothing. Users with auto-mute on are muted right after.
3. **All clear:** When no alerts remain, users with clear messages on get `🟢 All clear` (muted users too), if they had at least one of that alert's levels and types on. Then all mutes are lifted.
4. If an alert has no `alert_level` in the API data, the level is shown as `🚨 Alert`.
5. If the API request fails, the bot skips that check. It does not send a false all-clear.

---

## 📨 Message Types

Format: `<level> — <threats> threat`, or `🟢 All clear`.

| Level | When |
|-------|------|
| `🔴 Red level` | API `alert_level` is `red` |
| `🟡 Yellow level` | API `alert_level` is `yellow` |
| `🚨 Alert` | Alert active, no `alert_level` |

Each level can be turned off: the first row in Settings → 🎛 Alert types (`🔴 Red level`, `🟡 Yellow level`, `🚨 No level`).

Threat words, most dangerous first. Several active groups are joined: `missile, drone threat`.

| Word | Alert types |
|------|-------------|
| `nuclear` | `nuclear` |
| `chemical` | `chemical` |
| `missile` | `ballistic_missiles`, `cruise_missiles`, `unspecified_missiles`, `mig31k_departure` |
| `guided bomb` | `guided_aerial_bombs` |
| `aviation` | `strategic_aircraft_activity`, `tactic_aircraft_activity` |
| `drone` | `drones` |
| `artillery` | `artillery_shelling` |
| `urban combat` | `urban_fights` |
| `air raid` | Only when none of the above: `air_raid`, `air_defense`, `unknown` |

Toggleable alert types (Settings → 🎛 Alert types):

| Key | Label |
|-----|-------|
| `air_raid` | 🚨 Air raid |
| `artillery_shelling` | 💥 Artillery shelling |
| `urban_fights` | ⚔️ Urban fights |
| `chemical` | ☣️ Chemical danger |
| `nuclear` | ☢️ Nuclear danger |
| `ballistic_missiles` | 🚀 Ballistic missiles |
| `cruise_missiles` | 🚀 Cruise missiles |
| `unspecified_missiles` | 🚀 Missiles (unspecified) |
| `mig31k_departure` | ✈️ MiG-31K departure (Kinzhal) |
| `strategic_aircraft_activity` | ✈️ Strategic aviation |
| `tactic_aircraft_activity` | ✈️ Tactical aviation |
| `drones` | 🛸 Drones (UAV) |
| `guided_aerial_bombs` | 💣 Guided aerial bombs |
| `air_defense` | 🛡 Air defense active |
| `unknown` | ❓ Unknown threat |

---

## 🛠 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Vanago-official/AirAlert.git
cd AirAlert
```

### 2. Create a virtual environment and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy the example and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=your_telegram_bot_token      # Token from @BotFather
ALARM=your_alerts_api_token            # Token from https://alerts.in.ua/
```

### 4. Configure your city
Edit `config.cfg`:
```ini
[Settings]
CITY=м. Київ
```

> **Note:** `CITY` must match the exact `location_title` from the alerts.in.ua API.

### 5. Run the bot
```bash
python main.py
```

---

## 🤖 Bot Buttons

**Main menu**

| Button | Action |
|--------|--------|
| 🔕 Mute | Silence alerts until all alerts end |
| 🔔 Unmute | Resume receiving alerts |
| 📊 Status | Show current alert state and user settings |
| ⚙️ Settings | Open the settings menu |
| ℹ️ Info | About the bot |

**Settings menu**

| Button | Action |
|--------|--------|
| 🟢 Activate | Subscribe to alerts |
| 🛑 Deactivate | Unsubscribe from all alerts |
| 🟢 Send clear / 🔴 Don't send clear | Toggle end-of-alert messages |
| 🔕 Auto-mute: ON / 🔔 Auto-mute: OFF | Toggle auto-mute until all-clear |
| 🎛 Alert types | Turn each alert level and type on (✅) or off (❌), or all at once |
| 🔙 Back | Return to the main menu |

---

## 🧯 Troubleshooting

| Problem | Fix |
|---------|-----|
| `no such column` in SQLite | Update to the latest `database.py` and restart. Schema changes are applied automatically. |

---

## ⚠️ Disclaimer

This bot is a personal project and is intended as an **auxiliary tool only**. It does not replace official emergency alert systems. Stay safe! 🇺🇦
