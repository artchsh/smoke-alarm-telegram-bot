import logging
import os
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Йо! Это Чилл-Зона Бот. 🚬\n"
        "Я чекаю всех, кто пишет в чат, и добавляю в сквад.\n"
        "Юзай /smoke, чтобы созвать всех на перекур!\n"
        "Юзай /smoke_stats, чтобы чекнуть статистику.\n"
        "Юзай /smoke_leave, если хочешь ливнуть из рассылки.\n"
        "Юзай /smoke_join, чтобы вернуться обратно."
    )
    # Capture the user who started the bot
    await capture_user(update, context)

async def capture_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.effective_chat:
        user = update.effective_user
        chat = update.effective_chat
        
        update.effective_chat.get_administrators
        
        # Only relevant for group chats, but we can support private too if needed.
        # The requirement is "group chat", but storing private chats doesn't hurt.
        if chat.type in ['group', 'supergroup']:
            database.add_or_update_user(
                user.id, 
                chat.id, 
                user.mention_html()
            )

async def smoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caller_id = update.effective_user.id
    
    # Ensure the caller is captured/updated
    await capture_user(update, context)
    
    # Register all admins automatically
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if not admin.user.is_bot:
                database.add_or_update_user(admin.user.id, chat_id, admin.user.mention_html())
    except Exception as e:
        logging.error(f"Error fetching admins: {e}")

    users = database.get_active_users(chat_id)
    
    # Filter out the caller
    mentions = [name for uid, name in users if uid != caller_id]
    
    if not mentions:
        await update.message.reply_text("Эй, тут пусто! Либо ты один, либо все ливнули. 🗿")
        return

    # Log the event
    database.log_smoke_event(chat_id, caller_id)

    mentions_str = " ".join(mentions)
    message_template = random.choice(SMOKE_MESSAGES)
    text = message_template.format(mentions=mentions_str)
    
    await update.message.reply_html(text)

async def smoke_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await capture_user(update, context)
    
    today, week = database.get_smoke_stats(chat_id)
    
    text = (
        f"📊 **Стата по перекурам:**\n\n"
        f"🔥 Сегодня: **{today}** раз(а)\n"
        f"📅 За неделю: **{week}** раз(а)\n\n"
        f"Легкие в шоке! 💀"
    )
    await update.message.reply_markdown(text)

async def smoke_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Ensure user exists in DB first (in case they lurked until now)
    await capture_user(update, context)
    
    database.set_user_active(user.id, chat_id, False)
    await update.message.reply_text(f"Ок, {user.first_name}, не душни, убрал тебя. 🫡")

async def smoke_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Ensure user exists/update name
    await capture_user(update, context)
    
    database.set_user_active(user.id, chat_id, True)
    await update.message.reply_text(f"Опа, {user.first_name} снова с нами! Велкам бэк. 😎")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Please set it in your environment or .env file.")
        return

    # Initialize Database
    database.init_db()

    application = ApplicationBuilder().token(token).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("smoke", smoke))
    application.add_handler(CommandHandler("smoke_stats", smoke_stats))
    application.add_handler(CommandHandler("smoke_leave", smoke_leave))
    application.add_handler(CommandHandler("smoke_join", smoke_join))

    # Capture all messages to register users
    # We use a separate group so it doesn't stop other handlers
    application.add_handler(MessageHandler(filters.ALL, capture_user), group=1)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
