import logging
import os
import random
import datetime
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import database

class TelegramLogFilter(logging.Filter):
    def filter(self, record):
        return not (record.name.startswith('telegram') or 
                   ' telegram' in record.name.lower() or
                   record.levelno < logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
handler.addFilter(TelegramLogFilter())
logger.addHandler(handler)

file_handler = logging.FileHandler('bot.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.addFilter(TelegramLogFilter())
logger.addHandler(file_handler)

def log_action(action: str, details: str = ""):
    logger.info(f"ACTION: {action} | {details}".strip())

BOT_USERNAME = None

WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json?key=3d10f31522e649a9803151553240411&q=Almaty&aqi=no"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast?latitude=43.25&longitude=76.9167&daily=weather_code,temperature_2m_max,temperature_2m_min,sunset,sunrise,rain_sum,snowfall_sum&current=temperature_2m&timezone=auto&forecast_days=1"

WMO_WEATHER_CODES = {
    0: "Ясно ☀️",
    1: "Малооблачно 🌤️",
    2: "Облачно 🌥️",
    3: "Пасмурно ☁️",
    45: "Туман 🌫️",
    48: "Изморозь 🌫️",
    51: "Морось 🌦️",
    53: "Умеренная морось 🌧️",
    55: "Сильная морось 🌧️",
    56: "Ледяная морось 🥶",
    57: "Сильная ледяная морось 🥶",
    61: "Слабый дождь 🌧️",
    63: "Умеренный дождь 🌧️",
    64: "Сильный дождь 🌧️",
    65: "Очень сильный дождь 🌧️",
    66: "Ледяной дождь 🥶",
    67: "Сильный ледяной дождь 🥶",
    71: "Слабый снег 🌨️",
    73: "Умеренный снег 🌨️",
    75: "Сильный снег 🌨️",
    77: "Снежные зёрна 🌨️",
    80: "Слабый снег с дождем 🌨️",
    81: "Умеренный снег с дождем 🌨️",
    82: "Сильный снег с дождем 🌨️",
    85: "Слабый снегопад ❄️",
    86: "Сильный снегопад ❄️",
    95: "Гроза ⛈️",
    96: "Гроза с градом ⛈️",
    99: "Сильная гроза с градом ⛈️",
}

TRACKED_CHATS = set()

SMOKE_MESSAGES = [
    "🚬 ГО КУРИТЬ! 🚬\n{mentions}\n\nНу че, народ, погнали дымить? 😮‍💨",
    "🔥 ВРЕМЯ ПЫХНУТЬ! 🔥\n{mentions}\n\nКто не курит, тот работает (или нет). Го на улицу! 🚶‍♂️",
    "🌬️ S M O K E   B R E A K 🌬️\n{mentions}\n\nЛегкие сами себя не засорят. Погнали! 💀",
    "🚬 ПЕРЕКУРЧИК! 🚬\n{mentions}\n\nХватит пялиться в монитор, пошли подышим свежим (табачным) воздухом! 🌳",
    "😮‍💨 ДЫМОВАЯ ЗАВЕСА 😮‍💨\n{mentions}\n\nСбор у курилки через 5 минут! Кто последний - тот лох. 🏃💨",
    "🚬 NICOTINE CALLING 🚬\n{mentions}\n\nВаш организм требует яда. Не заставляйте его ждать! ☠️",
    "🚬 КУРИТЬ ХОЧУ - НЕ МОГУ! 🚬\n{mentions}\n\nСоставьте компанию, а то одному скучно стоять. 🥺",
    "🔥 FIRE IN THE HOLE! 🔥\n{mentions}\n\nПоджигай! Время сжечь пару палочек здоровья. 🔥",
    "🚬 5 МИНУТ ТИШИНЫ 🚬\n{mentions}\n\nИли не тишины, а сплетен у курилки. Го! 🗣️",
    "🚬 ВНИМАНИЕ, СПАСИБО ЗА ВНИМАНИЕ 🚬\n{mentions}\n\nОбъявляется всеобщая мобилизация в курилку. Форма одежды - парадная (с сигаретой). 🫡"
]

async def get_weather_text():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(WEATHER_API_URL)
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                # location = data.get("location", {})
                
                temp_c = current.get("temp_c")
                feelslike_c = current.get("feelslike_c")
                # condition = current.get("condition", {}).get("text")
                # wind_kph = current.get("wind_kph")
                
                # Determine emoji based on temp
                temp_emoji = "❄️" if temp_c < 0 else "☀️" if temp_c > 20 else "⛅"
                
                return (
                    f"\n\n🌡 <b>Погода:</b>\n"
                    f"{temp_emoji} Температура: <b>{temp_c}°C</b> (ощущается как {feelslike_c}°C)\n"
                    # f"☁️ Небо: {condition}\n"
                    # f"💨 Ветер: {wind_kph} км/ч"
                )
    except Exception as e:
        logging.error(f"Error fetching weather: {e}")
    return ""

async def get_open_meteo_weather():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(OPEN_METEO_URL, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                
                current = data.get("current", {})
                daily = data.get("daily", {})
                daily_units = data.get("daily_units", {})
                
                temp_current = current.get("temperature_2m", 0)
                
                temp_max = daily.get("temperature_2m_max", [0])[0]
                temp_min = daily.get("temperature_2m_min", [0])[0]
                weather_code = daily.get("weather_code", [0])[0]
                sunrise = daily.get("sunrise", [""])[0]
                sunset = daily.get("sunset", [""])[0]
                rain_sum = daily.get("rain_sum", [0])[0]
                snowfall_sum = daily.get("snowfall_sum", [0])[0]
                
                weather_desc = WMO_WEATHER_CODES.get(weather_code, "Неизвестно")
                
                if sunrise:
                    sunrise_time = sunrise.split("T")[1][:5] if "T" in sunrise else sunrise
                else:
                    sunrise_time = "--:--"
                
                if sunset:
                    sunset_time = sunset.split("T")[1][:5] if "T" in sunset else sunset
                else:
                    sunset_time = "--:--"
                
                emoji = "❄️" if temp_current < -10 else "☁️" if temp_current < 0 else "🌤️" if temp_current < 10 else "☀️"
                
                return (
                    f"{emoji} <b>Погода в Алматы:</b>\n\n"
                    f"🌡️ Сейчас: <b>{temp_current}°C</b>\n"
                    f"📈 Макс: {temp_max}°C / Мин: {temp_min}°C\n"
                    f"🌥️ Условия: <b>{weather_desc}</b>\n"
                    f"🌅 Восход: <b>{sunrise_time}</b>\n"
                    f"🌇 Закат: <b>{sunset_time}</b>\n"
                    f"💧 Осадки: <b>{rain_sum} мм</b>\n"
                    f"❄️ Снег: <b>{snowfall_sum} см</b>"
                )
    except Exception as e:
        logging.error(f"Error fetching Open-Meteo weather: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    log_action("START", f"User {user.id} ({user.first_name}) started bot in chat {chat.id}")
    await update.message.reply_html(
        "Йо! Это Чилл-Зона Бот. 🚬\n"
        "Я чекаю всех, кто пишет в чат, и добавляю в сквад.\n"
        "Юзай /smoke, чтобы созвать всех на перекур!\n"
        "Юзай /smoke_stats, чтобы чекнуть статистику.\n"
        "Юзай /leaderboard, чтобы глянуть топ курильщиков.\n"
        "Юзай /weather_info, чтобы узнать погоду.\n"
        "Юзай /weather_subscribe, чтобы получать погоду каждый день в 9:00.\n"
        "Юзай /smoke_leave, если хочешь ливнуть из рассылки.\n"
        "Юзай /smoke_join, чтобы вернуться обратно."
    )
    await capture_user(update, context)

async def capture_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.effective_chat:
        user = update.effective_user
        chat = update.effective_chat
        
        update.effective_chat.get_administrators
        
        if chat.type in ['group', 'supergroup']:
            database.add_or_update_user(
                user.id, 
                user.mention_html()
            )
            log_action("USER_CAPTURED", f"User {user.id} ({user.first_name}) captured")

async def smoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caller_id = update.effective_user.id
    caller_name = update.effective_user.first_name

    log_action("SMOKE_COMMAND", f"User {caller_id} ({caller_name}) called /smoke in chat {chat_id}")

    await capture_user(update, context)

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if not admin.user.is_bot:
                database.add_or_update_user(admin.user.id, admin.user.mention_html())
    except Exception as e:
        logging.error(f"Error fetching admins: {e}")

    users = database.get_active_users()
    mentions = [name for uid, name in users if uid != caller_id]

    if not mentions:
        log_action("SMOKE_FAILED", f"No active users in chat {chat_id}")
        await update.message.reply_text("Эй, тут пусто! Либо ты один, либо все ливнули. 🗿")
        return

    database.log_smoke_event(chat_id, caller_id)
    log_action("SMOKE_LOGGED", f"Smoke event logged for user {caller_id} in chat {chat_id}")

    mentions_str = " ".join(mentions)
    message_template = random.choice(SMOKE_MESSAGES)

    weather_text = await get_weather_text()
    text = message_template.format(mentions=mentions_str) + weather_text

    # Inline keyboards are shared for the whole chat. We must keep a single button
    # and change its label based on who clicked (per-user), not render one button
    # per participant.
    keyboard = [[InlineKeyboardButton("Я иду! 🚬", callback_data="toggle_0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    sent_message = await update.message.reply_html(text, reply_markup=reply_markup)
    log_action("SMOKE_SENT", f"Smoke message sent in chat {chat_id}, message_id={sent_message.message_id}")

    actual_message_id = sent_message.message_id

    # Auto-join caller and then update the single button.
    database.toggle_smoke_participation(caller_id, chat_id, actual_message_id)
    log_action("SMOKE_AUTO_JOIN", f"Caller {caller_id} ({caller_name}) automatically joined smoke event")

    updated_reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Я иду! 🚬", callback_data=f"toggle_{actual_message_id}")]]
    )
    await sent_message.edit_reply_markup(reply_markup=updated_reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("toggle_"):
        return

    user = query.from_user
    chat_id = query.message.chat_id
    message_id = int(query.data.split("_")[1])

    joined = database.toggle_smoke_participation(user.id, chat_id, message_id)
    status = "joined" if joined else "left"
    log_action("BUTTON_CLICK", f"User {user.id} ({user.first_name}) {status} smoke event in chat {chat_id}")

    user_line = f"- {user.mention_html()}"
    current_text = query.message.text_html

    weather_marker = "\n\n🌡 <b>Погода:</b>"
    header = "\n\n😎 <b>Крутышки, которые идут курить:</b>"


    if weather_marker in current_text:
        parts = current_text.split(weather_marker)
        main_part = parts[0]
        weather_part = weather_marker + parts[1]
    else:
        main_part = current_text
        weather_part = ""

    if header in main_part:
        subparts = main_part.split(header)
        intro = subparts[0]
        list_content = subparts[1]

        lines = [line.strip() for line in list_content.split("\n") if line.strip()]

        if user_line in lines:
            lines.remove(user_line)
        else:
            lines.append(user_line)

        if not lines:
            new_main = intro
        else:
            new_main = intro + header + "\n" + "\n".join(lines)
    else:
        new_main = main_part + header + "\n" + user_line

    new_text = new_main + weather_part

    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Я иду! 🚬", callback_data=f"toggle_{message_id}")]]
    )

    if new_text != current_text:
        await query.edit_message_text(new_text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await query.edit_message_reply_markup(reply_markup=reply_markup)


async def smoke_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    log_action("STATS_COMMAND", f"User {user.id} ({user.first_name}) requested stats in chat {chat_id}")
    await capture_user(update, context)
    
    today, week = database.get_smoke_stats(chat_id)
    today_leaders, week_leaders = database.get_smoke_leaderboard(chat_id)
    month_count, top_smoker, month_leaders = database.get_monthly_stats(chat_id)
    
    def format_leaders(leaders):
        if not leaders:
            return "Пока никто..."
        return "\n".join([f"{i+1}. {name}: <b>{count}</b>" for i, (name, count) in enumerate(leaders)])
    
    top_smoker_text = f"{top_smoker[0]}: <b>{top_smoker[1]}</b>" if top_smoker else "Пока никто..."
    
    text = (
        f"📊 <b>Стата по перекурам:</b>\n\n"
        f"🔥 <b>Общие вызовы:</b>\n"
        f"Сегодня: <b>{today}</b> раз(а)\n"
        f"За неделю: <b>{week}</b> раз(а)\n"
        f"За месяц: <b>{month_count}</b> раз(а)\n\n"
        f"🏆 <b>Топ курильщиков (сегодня):</b>\n"
        f"{format_leaders(today_leaders)}\n\n"
        f"👑 <b>Топ курильщиков (неделя):</b>\n"
        f"{format_leaders(week_leaders)}\n\n"
        f"🥇 <b>Топ месяца:</b>\n"
        f"{top_smoker_text}\n\n"
        f"Легкие в шоке! 💀"
    )
    await update.message.reply_html(text)

async def smoke_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    log_action("LEAVE_COMMAND", f"User {user.id} ({user.first_name}) left smoke notifications in chat {chat_id}")
    
    await capture_user(update, context)
    
    if not database.is_user_active(user.id):
        await update.message.reply_html(f"Ты и так не в рассылке")
        return
    
    database.set_user_active(user.id, False)
    await update.message.reply_html(f"Ок, {user.first_name}, не душни, убрал тебя. 🫡")

async def smoke_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    log_action("JOIN_COMMAND", f"User {user.id} ({user.first_name}) joined smoke notifications in chat {chat_id}")
    
    await capture_user(update, context)
    
    if database.is_user_active(user.id):
        await update.message.reply_html(f"Ты и так в рассылке")
        return
    
    database.set_user_active(user.id, True)
    await update.message.reply_html(f"Опа, {user.first_name} снова с нами! Велкам бэк. 😎")

async def weather_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    log_action("WEATHER_INFO", f"User {user.id} ({user.first_name}) requested weather in chat {chat_id}")
    
    weather_text = await get_open_meteo_weather()
    
    if weather_text:
        keyboard = [[InlineKeyboardButton("Обновить 🔄", callback_data="refresh_weather")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(weather_text, reply_markup=reply_markup)
    else:
        await update.message.reply_html("Не удалось получить погоду. Попробуй позже. 😔")

async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    log_action("DAILY_WEATHER", f"Sending daily weather to chat {chat_id}")

    weather_text = await get_open_meteo_weather()

    if weather_text:
        try:
            # Daily message should be just the weather info.
            text = weather_text
            await context.bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            log_action("DAILY_WEATHER_ERROR", f"Failed to send weather to {chat_id}: {e}")

def schedule_daily_weather(application, chat_id):
    job_queue = application.job_queue
    job_queue.run_daily(
        send_daily_weather,
        time=datetime.time(hour=9, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=6))),
        days=(0, 1, 2, 3, 4),
        chat_id=chat_id,
        name=f"daily_weather_{chat_id}"
    )
    log_action("SCHEDULE_WEATHER", f"Scheduled daily weather for chat {chat_id} at 9:00 AM")

async def weather_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id in TRACKED_CHATS:
        TRACKED_CHATS.remove(chat_id)
        job_queue = context.application.job_queue
        jobs = job_queue.get_jobs_by_name(f"daily_weather_{chat_id}")
        for job in jobs:
            job.schedule_removal()
        log_action("WEATHER_UNSUBSCRIBE", f"User {user.id} unsubscribed from daily weather in chat {chat_id}")
        await update.message.reply_html("❌ Ежедневная погода отключена. Используй команду снова, чтобы включить.")
    else:
        TRACKED_CHATS.add(chat_id)
        schedule_daily_weather(context.application, chat_id)
        log_action("WEATHER_SUBSCRIBE", f"User {user.id} subscribed to daily weather in chat {chat_id}")
        await update.message.reply_html("✅ Ежедневная погода включена! Каждый будний день в 9:00 утра я буду присылать сводку. ☀️")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    log_action("LEADERBOARD_COMMAND", f"User {user.id} ({user.first_name}) requested leaderboard in chat {chat_id}")
    await capture_user(update, context)

    keyboard = [
        [InlineKeyboardButton("Сегодня", callback_data="leaderboard_today"),
         InlineKeyboardButton("Неделя", callback_data="leaderboard_week")],
        [InlineKeyboardButton("Месяц", callback_data="leaderboard_month"),
         InlineKeyboardButton("Всё время", callback_data="leaderboard_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        "🏆 <b>Топ курильщиков:</b>\n\n"
        "Выбери период:",
        reply_markup=reply_markup
    )


async def leaderboard_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat_id = query.message.chat_id

    period_map = {
        "leaderboard_today": ("Сегодня", "today"),
        "leaderboard_week": ("Неделя", "week"),
        "leaderboard_month": ("Месяц", "month"),
        "leaderboard_all": ("Всё время", "all"),
    }

    period_key = query.data
    if period_key not in period_map:
        return

    period_name, period = period_map[period_key]
    log_action("LEADERBOARD_BUTTON", f"User {user.id} ({user.first_name}) viewed {period_name} leaderboard in chat {chat_id}")

    leaders = database.get_smoke_leaderboard_for_period(chat_id, period)

    if not leaders:
        text = f"🏆 <b>Топ за {period_name}:</b>\n\nПока никто не отметился..."
    else:
        lines = [f"🏆 <b>Топ за {period_name}:</b>\n"]
        for i, (name, count) in enumerate(leaders, start=1):
            lines.append(f"{i}. {name}: <b>{count}</b>")
        text = "\n".join(lines)

    keyboard = [
        [InlineKeyboardButton("Сегодня", callback_data="leaderboard_today"),
         InlineKeyboardButton("Неделя", callback_data="leaderboard_week")],
        [InlineKeyboardButton("Месяц", callback_data="leaderboard_month"),
         InlineKeyboardButton("Всё время", callback_data="leaderboard_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    
    global BOT_USERNAME
    if BOT_USERNAME is None:
        try:
            me = await context.bot.get_me()
            BOT_USERNAME = me.username.lower()
        except:
            return
    
    message_text = update.message.text or ""
    message_text_lower = message_text.lower()
    
    bot_mentioned = (
        f"@{BOT_USERNAME}" in message_text or
        BOT_USERNAME in message_text_lower
    )
    
    if bot_mentioned:
        log_action("BOT_MENTIONED", f"User {update.effective_user.id} mentioned bot")
        await smoke(update, context)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Please set it in your environment or .env file.")
        return

    database.init_db()

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("smoke", smoke))
    application.add_handler(CommandHandler("smoke_stats", smoke_stats))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("smoke_leave", smoke_leave))
    application.add_handler(CommandHandler("smoke_join", smoke_join))
    application.add_handler(CommandHandler("weather_info", weather_info))
    application.add_handler(CommandHandler("weather_subscribe", weather_subscribe))
    # Register more specific callback handlers first.
    application.add_handler(CallbackQueryHandler(leaderboard_button_handler, pattern=r"^leaderboard_"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern=r"^toggle_"))

    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_mention))
    application.add_handler(MessageHandler(filters.ALL, capture_user), group=1)

    for chat_id in TRACKED_CHATS:
        schedule_daily_weather(application, chat_id)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
