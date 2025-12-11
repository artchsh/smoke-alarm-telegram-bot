import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db(db_path="smoke_bot.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER,
            chat_id INTEGER,
            mention_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smoke_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_smoke_event(chat_id, user_id, db_path="smoke_bot.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO smoke_events (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
    conn.commit()
    conn.close()

def get_smoke_stats(chat_id, db_path="smoke_bot.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count for today (local time might be tricky with SQLite default UTC, but let's assume 'start of day' in UTC or just last 24h? 
    # 'start of day' is better for "today". SQLite 'now' is UTC.
    # Let's use 'localtime' modifier if we want server local time, or just UTC. 
    # Simple approach: date('now') matches YYYY-MM-DD.
    
    cursor.execute("""
        SELECT count(*) FROM smoke_events 
        WHERE chat_id = ? AND date(timestamp) = date('now')
    """, (chat_id,))
    today_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT count(*) FROM smoke_events 
        WHERE chat_id = ? AND timestamp >= datetime('now', '-7 days')
    """, (chat_id,))
    week_count = cursor.fetchone()[0]
    
    conn.close()
    return today_count, week_count

def add_or_update_user(user_id, chat_id, mention_name, db_path="smoke_bot.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if user exists
        cursor.execute("SELECT is_active FROM participants WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        result = cursor.fetchone()
        
        if result is None:
            # New user, default active
            cursor.execute(
                "INSERT INTO participants (user_id, chat_id, mention_name, is_active) VALUES (?, ?, ?, 1)",
                (user_id, chat_id, mention_name)
            )
            logger.info(f"Added new user {mention_name} ({user_id}) in chat {chat_id}")
        else:
            # Update mention name just in case, but don't change is_active status
            cursor.execute(
                "UPDATE participants SET mention_name = ? WHERE user_id = ? AND chat_id = ?",
                (mention_name, user_id, chat_id)
            )
    except Exception as e:
        logger.error(f"Error adding/updating user: {e}")
    finally:
        conn.commit()
        conn.close()

def set_user_active(user_id, chat_id, is_active, db_path="smoke_bot.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE participants SET is_active = ? WHERE user_id = ? AND chat_id = ?",
        (1 if is_active else 0, user_id, chat_id)
    )
    if cursor.rowcount == 0:
        # If user tried to leave/join but wasn't in DB yet (e.g. never spoke), insert them
        # If leaving, insert as inactive. If joining, insert as active.
        # We need a mention name though. This function might need to be called with mention_name if we want to support this edge case perfectly.
        # For now, we assume the user has interacted or we ignore. 
        # Actually, if they run a command, they are interacting. We should probably capture them in the command handler first.
        pass
    conn.commit()
    conn.close()

def get_active_users(chat_id, db_path="smoke_bot.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, mention_name FROM participants WHERE chat_id = ? AND is_active = 1", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    return users
