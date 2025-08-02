import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
import yaml

# Загрузка конфигурации из YAML
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

API_TOKEN = config["api_token"]
OWNER_ID = config["owner_id"]
CHANNEL_ID = int(config["channel_id"])  # убедись, что int!

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

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

def block_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def unblock_user(user_id: int):
    cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
    conn.commit()

def is_blocked(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None


@dp.message(Command("start"))
async def start_command(message: Message):
    await message.reply(f"Привет! Твой Telegram ID: {message.from_user.id}")

@dp.message(Command("ban"))
async def ban_user(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        user_id = int(message.text.split(maxsplit=1)[1])
        block_user(user_id)
        await message.reply(f"Пользователь {user_id} заблокирован.")
    except:
        await message.reply("Используй: /ban <user_id>")

@dp.message(Command("unban"))
async def unban_user(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        user_id = int(message.text.split(maxsplit=1)[1])
        unblock_user(user_id)
        await message.reply(f"Пользователь {user_id} разблокирован.")
    except:
        await message.reply("Используй: /unban <user_id>")

ideas_cache = {}

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "без ника"

    if is_blocked(user_id):
        await message.reply("Вы заблокированы.")
        return

    text = (message.text or message.caption or "").strip()

    if not text and message.content_type not in ("photo", "video", "audio", "voice", "document", "animation"):
        await message.reply("Пожалуйста, отправьте текст, фото или другое медиа.")
        return

    # Определяем тип медиа и file_id, если есть
    file_id = None
    content_type = None

    if message.content_type == "photo":
        file_id = message.photo[-1].file_id  # самое большое фото
        content_type = "photo"
    elif message.content_type == "video":
        file_id = message.video.file_id
        content_type = "video"
    elif message.content_type == "audio":
        file_id = message.audio.file_id
        content_type = "audio"
    elif message.content_type == "voice":
        file_id = message.voice.file_id
        content_type = "voice"
    elif message.content_type == "document":
        file_id = message.document.file_id
        content_type = "document"
    elif message.content_type == "animation":
        file_id = message.animation.file_id
        content_type = "animation"
    else:
        content_type = "text"

    message_key = message.message_id

    ideas_cache[message_key] = {
        "user_id": user_id,
        "username": username,
        "text": text.strip(),
        "content_type": content_type,
        "file_id": file_id,
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{message_key}")],
        [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{message_key}")],
        [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{message_key}")]
    ])

    await bot.send_message(
        OWNER_ID,
        f"<b>Сообщение от @{username} (ID: {user_id}):</b>\n\n{text.strip()}",
        reply_markup=keyboard
    )

    await message.reply("Спасибо! Сообщение отправлено на модерацию.")


@dp.callback_query()
async def callback_handler(callback_query: CallbackQuery):
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    data = callback_query.data
    action, message_key_str = data.split(":")
    message_key = int(message_key_str)

    if message_key not in ideas_cache:
        await callback_query.answer("Данные не найдены", show_alert=True)
        return

    idea = ideas_cache[message_key]
    user_id = idea["user_id"]
    username = idea["username"]
    text = idea["text"]
    content_type = idea["content_type"]
    file_id = idea["file_id"]

    author_mention = (
        f"<a href='tg://user?id={user_id}'>@{username}</a>"
        if username != "без ника" else f"<a href='tg://user?id={user_id}'>Пользователь</a>"
    )

    if action == "approve":
        # Отправляем в канал с учётом типа контента
        if content_type == "text":
            await bot.send_message(CHANNEL_ID, f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        elif content_type == "photo":
            await bot.send_photo(CHANNEL_ID, photo=file_id, caption=f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        elif content_type == "video":
            await bot.send_video(CHANNEL_ID, video=file_id, caption=f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        elif content_type == "audio":
            await bot.send_audio(CHANNEL_ID, audio=file_id, caption=f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        elif content_type == "voice":
            await bot.send_voice(CHANNEL_ID, voice=file_id, caption=f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        elif content_type == "document":
            await bot.send_document(CHANNEL_ID, document=file_id, caption=f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        elif content_type == "animation":
            await bot.send_animation(CHANNEL_ID, animation=file_id, caption=f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")
        else:
            # На всякий случай, если тип неизвестен
            await bot.send_message(CHANNEL_ID, f"Сообщение от {author_mention}:\n\n{text}", parse_mode="HTML")

        await callback_query.message.edit_reply_markup()
        await callback_query.answer("Опубликовано ✅")

    elif action == "idea":
        cursor.execute(
            "INSERT INTO ideas (user_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, username, text, datetime.now().isoformat())
        )
        conn.commit()
        await callback_query.message.edit_reply_markup()
        await callback_query.answer("Сохранено в базу 💡")

    elif action == "reject":
        await callback_query.message.edit_reply_markup()
        await callback_query.answer("Отклонено 🚫")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
