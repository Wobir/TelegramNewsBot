import sqlite3

conn = sqlite3.connect("bot_db.sqlite3")
cursor = conn.cursor()

# === Инициализация таблиц ===
cursor.executescript("""
    CREATE TABLE IF NOT EXISTS blocked_users (
        user_id INTEGER PRIMARY KEY
    );
    
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        message TEXT,
        timestamp TEXT
    );
""")
conn.commit()

# === Функции работы с блокировкой пользователей ===
def is_blocked(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def block_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def unblock_user(user_id: int):
    cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
    conn.commit()

def get_blocked_users():
    cursor.execute("SELECT user_id FROM blocked_users ORDER BY user_id")
    return cursor.fetchall()

# === Работа с идеями ===
def save_idea(user_id: int, username: str, message: str, timestamp: str):
    cursor.execute(
        "INSERT INTO ideas (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, username, message, timestamp)
    )
    conn.commit()

def get_latest_ideas(limit=20):
    cursor.execute(
        "SELECT id, user_id, username, message, timestamp FROM ideas ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()
