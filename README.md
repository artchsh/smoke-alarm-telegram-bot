# Smoke Alarm Telegram Bot 🚬

A fun, Gen-Z style Telegram bot that helps coordinate smoke breaks for your squad. Now in Russian! 🇷🇺

## Features

- **Automatic Registration**: The bot automatically registers anyone who sends a message in the group.
- **Interactive Smoke Calls**:
    -   `/smoke` - Mentions everyone in the squad with a random fun message (Gen-Z style 🤪).
    -   **Weather Info**: Shows current weather in Almaty. 🌡️
    -   **"I'm going!" Button**: Interactive button to track who is actually going.
- **Leaderboards**:
    -   `/smoke_stats` - Shows smoke stats and a leaderboard of top smokers for the day/week. 🏆
- **Management**:
    -   `/smoke_leave` - Opt-out of notifications.
    -   `/smoke_join` - Opt-in again.

## Setup

1.  **Get a Bot Token**: Talk to [@BotFather](https://t.me/BotFather) on Telegram to create a new bot and get your token.
2.  **Configure Environment**:
    -   Create a `.env` file.
    -   Add your token: `TELEGRAM_BOT_TOKEN=your_token_here`

### Running with Docker (Recommended)

```bash
docker compose up -d
```

### Running Locally

1.  **Install Dependencies**:
    ```bash
    uv sync
    ```
2.  **Run the Bot**:
    ```bash
    uv run main.py
    ```

## Persistence

The bot uses SQLite to save participants and stats. When using Docker, data is persisted in the `./data` directory.
