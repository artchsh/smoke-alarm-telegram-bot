# Smoke Alarm Telegram Bot 🚬

A fun, Gen-Z style Telegram bot that helps coordinate smoke breaks for your squad. Now in Russian! 🇷🇺

## Features

- **Automatic Registration**: The bot automatically registers anyone who sends a message in the group.
- **Interactive Smoke Calls**:
    - `/smoke` - Mentions everyone in the squad with a random fun message (Gen-Z style 🤪).
    - **Bot Mention**: The bot also responds to being mentioned (e.g., `@botname`) with a smoke call.
    - **Weather Info**: Shows current weather in Almaty. 🌡️
    - **"I'm going!" Button**: Interactive button that toggles your participation. Changes to "Я передумал... 😢" when you've joined.
    - **Auto-join**: The person who calls smoke is automatically added to the participants list.
- **Leaderboards & Stats**:
    - `/smoke_stats` - Shows smoke stats and leaderboards for day/week/month. 🏆
    - `/smoke_history` - Interactive history viewer with buttons for Today/Week/Month/All time.
- **Weather Features**:
    - `/weather_info` - Get current weather forecast using Open-Meteo API.
    - `/weather_subscribe` - Toggle daily weather notifications at 9:00 AM on workdays.
- **Management**:
    - `/smoke_leave` - Opt-out of notifications (checks if already opted out).
    - `/smoke_join` - Opt-in again (checks if already opted in).

## Commands

Set these commands in BotFather:

```
start - Start the bot
smoke - Call a smoke break 🚬
smoke_stats - View smoke statistics 🏆
smoke_history - View smoke history 📜
weather_info - Get weather forecast 🌤️
weather_subscribe - Toggle daily weather 📅
smoke_leave - Leave smoke notifications
smoke_join - Join smoke notifications
```

## Setup

1. **Get a Bot Token**: Talk to [@BotFather](https://t.me/BotFather) on Telegram to create a new bot and get your token.
2. **Configure Environment**:
    - Create a `.env` file.
    - Add your token: `TELEGRAM_BOT_TOKEN=your_token_here`

### Running with Docker (Recommended)

```bash
docker compose up -d
```

### Running Locally

1. **Install Dependencies**:
    ```bash
    uv sync
    ```
2. **Run the Bot**:
    ```bash
    uv run main.py
    ```

## Persistence

The bot uses SQLite to save participants and stats. When using Docker, data is persisted in the `./data` directory.

## Database Migration

The bot automatically migrates from the old schema (user_id + chat_id as primary key) to the new schema (user_id only) on first run. Your data is preserved.

## Logging

All bot actions are logged to `bot.log` for debugging and monitoring.
