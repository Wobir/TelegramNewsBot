import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils import executor
from datetime import datetime
import yaml

# Загрузка конфигурации из YAML
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

API_TOKEN = config["api_token"]
OWNER_ID = config["owner_id"]
CHANNEL_ID = config["channel_id"]

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# --- База данных ---
conn = sqlite3.connect("bot_db.sqlite3")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS blocked_users (
    user_id INTEGER PRIMARY KEY
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    timestamp TEXT
)""")

conn.commit()

# --- Функции блокировки ---
def block_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def unblock_user(user_id: int):
    cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
    conn.commit()

def is_blocked(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# --- Команды ---
@dp.message_handler(commands=['start'])
async def start_command(message: Message):
    await message.reply(f"Привет! Твой Telegram ID: {message.from_user.id}")

@dp.message_handler(commands=['ban'])
async def ban_user(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        user_id = int(message.get_args())
        block_user(user_id)
        await message.reply(f"Пользователь {user_id} заблокирован.")
    except:
        await message.reply("Используй: /ban <user_id>")

@dp.message_handler(commands=['unban'])
async def unban_user(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        user_id = int(message.get_args())
        unblock_user(user_id)
        await message.reply(f"Пользователь {user_id} разблокирован.")
    except:
        await message.reply("Используй: /unban <user_id>")

# --- Приём сообщений ---
@dp.message_handler()
async def handle_message(message: Message):
    user_id = message.from_user.id

    if is_blocked(user_id):
        await message.reply("Вы заблокированы.")
        return

    text = message.text.strip()
    if not text:
        await message.reply("Пожалуйста, отправьте текстовую идею или новость.")
        return

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve:{user_id}"),
        InlineKeyboardButton("💡 В базу идей", callback_data=f"idea:{user_id}"),
        InlineKeyboardButton("🚫 Отклонить", callback_data=f"reject:{user_id}")
    )

    await bot.send_message(
        OWNER_ID,
        f"<b>Сообщение от @{message.from_user.username or 'без ника'} (ID: {user_id}):</b>\n\n{text}",
        reply_markup=keyboard
    )

    await message.reply("Спасибо! Сообщение отправлено на модерацию.")

# --- Обработка выбора ---
@dp.callback_query_handler()
async def callback_handler(callback_query: CallbackQuery):
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    data = callback_query.data
    action, user_id_str = data.split(":")
    user_id = int(user_id_str)
    msg = callback_query.message
    text = msg.text.split("):</b>\n\n", 1)[1]  # извлекаем содержимое

    if action == "approve":
        await bot.send_message(CHANNEL_ID, text)
        await callback_query.message.edit_reply_markup()
        await callback_query.answer("Опубликовано ✅")
    elif action == "idea":
        cursor.execute("INSERT INTO ideas (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, "@" + callback_query.from_user.username if callback_query.from_user.username else "", text, datetime.now().isoformat()))
        conn.commit()
        await callback_query.message.edit_reply_markup()
        await callback_query.answer("Сохранено в базу 💡")
    elif action == "reject":
        await callback_query.message.edit_reply_markup()
        await callback_query.answer("Отклонено 🚫")
