import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "smoke_bot.db")

def init_db(db_path=None):
    if db_path is None:
        db_path = DB_PATH
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smoke_participation (
            user_id INTEGER,
            chat_id INTEGER,
            message_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id, message_id)
        )
    """)
    conn.commit()
    conn.close()

def log_smoke_event(chat_id, user_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO smoke_events (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
    conn.commit()
    conn.close()

def toggle_smoke_participation(user_id, chat_id, message_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute(
        "SELECT 1 FROM smoke_participation WHERE user_id = ? AND chat_id = ? AND message_id = ?",
        (user_id, chat_id, message_id)
    )
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute(
            "DELETE FROM smoke_participation WHERE user_id = ? AND chat_id = ? AND message_id = ?",
            (user_id, chat_id, message_id)
        )
        joined = False
    else:
        cursor.execute(
            "INSERT INTO smoke_participation (user_id, chat_id, message_id) VALUES (?, ?, ?)",
            (user_id, chat_id, message_id)
        )
        joined = True
        
    conn.commit()
    conn.close()
    return joined

def get_smoke_leaderboard(chat_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Today
    cursor.execute("""
        SELECT p.mention_name, count(*) as count 
        FROM smoke_participation sp
        JOIN participants p ON sp.user_id = p.user_id AND sp.chat_id = p.chat_id
        WHERE sp.chat_id = ? AND date(sp.timestamp) = date('now')
        GROUP BY sp.user_id
        ORDER BY count DESC
        LIMIT 5
    """, (chat_id,))
    today_stats = cursor.fetchall()
    
    # Week
    cursor.execute("""
        SELECT p.mention_name, count(*) as count 
        FROM smoke_participation sp
        JOIN participants p ON sp.user_id = p.user_id AND sp.chat_id = p.chat_id
        WHERE sp.chat_id = ? AND sp.timestamp >= datetime('now', '-7 days')
        GROUP BY sp.user_id
        ORDER BY count DESC
        LIMIT 5
    """, (chat_id,))
    week_stats = cursor.fetchall()
    
    conn.close()
    return today_stats, week_stats

def get_smoke_stats(chat_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
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

def add_or_update_user(user_id, chat_id, mention_name, db_path=None):
    if db_path is None:
        db_path = DB_PATH
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

def set_user_active(user_id, chat_id, is_active, db_path=None):
    if db_path is None:
        db_path = DB_PATH
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

def get_active_users(chat_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, mention_name FROM participants WHERE chat_id = ? AND is_active = 1", (chat_id,))
    users = cursor.fetchall()
    conn.close()
    return users
