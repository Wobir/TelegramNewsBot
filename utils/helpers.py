from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID, OWNER_ID
from utils.state import ideas_cache

async def send_to_channel(bot, content_type, file_id, text, mention=None):
    caption = f"{text}\n\nСообщение от:\n <code>{mention}</code>"
    send_map = {
        "text": bot.send_message,
        "photo": bot.send_photo,
        "video": bot.send_video,
        "audio": bot.send_audio,
        "voice": bot.send_voice,
        "document": bot.send_document,
        "animation": bot.send_animation
    }

    if content_type == "text":
        await bot.send_message(CHANNEL_ID, caption)
    elif content_type in send_map:
        await send_map[content_type](CHANNEL_ID, file_id, caption=caption if file_id else None)
    else:
        await bot.send_message(CHANNEL_ID, caption)


async def process_submission(bot, message: Message, user_id, username, text, content_type, file_id):
    msg_id = message.message_id
    ideas_cache[msg_id] = {
        "user_id": user_id,
        "username": username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "text": text,
        "content_type": content_type,
        "file_id": file_id
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{msg_id}")],
        [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{msg_id}")],
        [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{msg_id}")],
        [InlineKeyboardButton(text="👤 Анонимно в канал", callback_data=f"anonymous:{msg_id}")]
    ])
    mention = f"<b>Сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"

    if content_type == "text" or not file_id:
        await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
    elif content_type == "album":
        await bot.send_media_group(OWNER_ID, media=file_id)
        await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
    else:
        send_map = {
            "photo": bot.send_photo, "video": bot.send_video,
            "audio": bot.send_audio, "voice": bot.send_voice,
            "document": bot.send_document, "animation": bot.send_animation
        }
        await send_map.get(content_type, bot.send_message)(OWNER_ID, file_id, caption=mention, reply_markup=keyboard)

    await message.reply("Спасибо! Сообщение отправлено на модерацию.")
