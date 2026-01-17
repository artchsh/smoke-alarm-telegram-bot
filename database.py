import sqlite3
import logging
import os

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('bot.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

DB_PATH = os.getenv("DB_PATH", "smoke_bot.db")

def init_db(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_version (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    cursor.execute("SELECT value FROM db_version WHERE key = 'schema_version'")
    version = cursor.fetchone()
    
    if version is None:
        cursor.execute("INSERT INTO db_version (key, value) VALUES ('schema_version', '1')")
        version = '1'
    
    if version[0] == '1':
        try:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='participants'")
            table_sql = cursor.fetchone()[0]
            if 'PRIMARY KEY (user_id, chat_id)' in table_sql or ('user_id, chat_id' in table_sql and 'PRIMARY KEY' in table_sql):
                logger.info("Detected old schema (user_id, chat_id) PK, migrating to new schema (user_id) PK...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS participants_new (
                        user_id INTEGER PRIMARY KEY,
                        mention_name TEXT,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO participants_new (user_id, mention_name, is_active)
                    SELECT user_id, mention_name, is_active FROM participants
                """)
                cursor.execute("DROP TABLE IF EXISTS participants")
                cursor.execute("ALTER TABLE participants_new RENAME TO participants")
                cursor.execute("UPDATE db_version SET value = '2' WHERE key = 'schema_version'")
                logger.info("Migration to new schema completed successfully")
        except Exception as e:
            logger.error(f"Migration error: {e}")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER PRIMARY KEY,
            mention_name TEXT,
            is_active BOOLEAN DEFAULT 1
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
        JOIN participants p ON sp.user_id = p.user_id
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
        JOIN participants p ON sp.user_id = p.user_id
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

def add_or_update_user(user_id, mention_name, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_active FROM participants WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result is None:
            cursor.execute(
                "INSERT INTO participants (user_id, mention_name, is_active) VALUES (?, ?, 1)",
                (user_id, mention_name)
            )
            logger.info(f"Added new user {mention_name} ({user_id})")
        else:
            cursor.execute(
                "UPDATE participants SET mention_name = ? WHERE user_id = ?",
                (mention_name, user_id)
            )
    except Exception as e:
        logger.error(f"Error adding/updating user: {e}")
    finally:
        conn.commit()
        conn.close()

def set_user_active(user_id, is_active, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE participants SET is_active = ? WHERE user_id = ?",
        (1 if is_active else 0, user_id)
    )
    conn.commit()
    conn.close()

def is_user_active(user_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM participants WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def get_active_users(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, mention_name FROM participants WHERE is_active = 1")
    users = cursor.fetchall()
    conn.close()
    return users

def get_monthly_stats(chat_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT count(*) FROM smoke_events 
        WHERE chat_id = ? AND timestamp >= datetime('now', '-30 days')
    """, (chat_id,))
    month_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT p.mention_name, count(*) as count 
        FROM smoke_events se
        JOIN participants p ON se.user_id = p.user_id
        WHERE se.chat_id = ? AND se.timestamp >= datetime('now', '-30 days')
        GROUP BY se.user_id
        ORDER BY count DESC
        LIMIT 1
    """, (chat_id,))
    top_smoker = cursor.fetchone()
    
    cursor.execute("""
        SELECT p.mention_name, count(*) as count 
        FROM smoke_participation sp
        JOIN participants p ON sp.user_id = p.user_id
        WHERE sp.chat_id = ? AND sp.timestamp >= datetime('now', '-30 days')
        GROUP BY sp.user_id
        ORDER BY count DESC
        LIMIT 5
    """, (chat_id,))
    month_leaders = cursor.fetchall()
    
    conn.close()
    return month_count, top_smoker, month_leaders

def get_smoke_history(chat_id, period='week', db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    period_map = {
        'today': "date(timestamp) = date('now')",
        'week': "timestamp >= datetime('now', '-7 days')",
        'month': "timestamp >= datetime('now', '-30 days')",
        'all': "1=1"
    }
    
    condition = period_map.get(period, period_map['week'])
    
    cursor.execute(f"""
        SELECT se.timestamp, p.mention_name 
        FROM smoke_events se
        JOIN participants p ON se.user_id = p.user_id
        WHERE se.chat_id = ? AND {condition}
        ORDER BY se.timestamp DESC
        LIMIT 50
    """, (chat_id,))
    events = cursor.fetchall()
    
    conn.close()
    return events

def get_db_connection(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    return sqlite3.connect(db_path)
