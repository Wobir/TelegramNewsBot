import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot_db.sqlite3"):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка работы с БД: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_db(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
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
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    # === Функции работы с блокировкой пользователей ===
    def is_blocked(self, user_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки блокировки: {e}")
            return False

    def block_user(self, user_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка блокировки пользователя: {e}")
            return False

    def unblock_user(self, user_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка разблокировки пользователя: {e}")
            return False

    def get_blocked_users(self) -> List[Tuple[int]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM blocked_users ORDER BY user_id")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения списка заблокированных: {e}")
            return []

    # === Работа с идеями ===
    def save_idea(self, user_id: int, username: str, message: str, timestamp: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO ideas (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
                    (user_id, username, message, timestamp)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка сохранения идеи: {e}")
            return False

    def get_latest_ideas(self, limit: int = 20) -> List[Tuple]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, user_id, username, message, timestamp FROM ideas ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения идей: {e}")
            return []

# Глобальный экземпляр БД
db = Database()