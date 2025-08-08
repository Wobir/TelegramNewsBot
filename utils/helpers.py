import asyncio
import logging
from typing import Optional
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID, OWNER_ID
from utils.state import state_manager

logger = logging.getLogger(__name__)

async def send_to_channel(bot, content_type: str, file_id: Optional[str], text: str, mention: Optional[str] = None, anonymous: bool = False) -> None:
    """Отправка сообщения в канал"""
    try:
        if anonymous:
            caption = text
        else:
            caption = f"{text}\n\nСообщение от:\n <code>{mention}</code>" if mention else text
        
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
            await bot.send_message(CHANNEL_ID, caption, parse_mode="HTML")
        elif content_type in send_map and file_id:
            await send_map[content_type](CHANNEL_ID, file_id, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(CHANNEL_ID, caption, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка отправки в канал: {e}")

async def process_submission(bot, message: Message, user_id: int, username: Optional[str], 
                           text: str, content_type: str, file_id: Optional[str], anonymous: bool = False) -> None:
    """Обработка отправленного сообщения"""
    try:
        msg_id = message.message_id
        state_manager.ideas_cache[msg_id] = {
            "user_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "text": text,
            "content_type": content_type,
            "file_id": file_id,
            "anonymous": anonymous,
            "timestamp": asyncio.get_event_loop().time()
        }

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{msg_id}")],
            [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{msg_id}")],
            [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{msg_id}")]
        ])
        
        if anonymous:
            mention = f"<b>Анонимное сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"
        else:
            mention = f"<b>Сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"

        if content_type == "text" or not file_id:
            await bot.send_message(OWNER_ID, mention, reply_markup=keyboard, parse_mode="HTML")
        elif content_type == "album":
            await bot.send_media_group(OWNER_ID, media=file_id)
            await bot.send_message(OWNER_ID, mention, reply_markup=keyboard, parse_mode="HTML")
        else:
            send_map = {
                "photo": bot.send_photo, "video": bot.send_video,
                "audio": bot.send_audio, "voice": bot.send_voice,
                "document": bot.send_document, "animation": bot.send_animation
            }
            
            send_func = send_map.get(content_type, bot.send_message)
            if content_type == "text":
                await send_func(OWNER_ID, mention, reply_markup=keyboard, parse_mode="HTML")
            else:
                await send_func(OWNER_ID, file_id, caption=mention, reply_markup=keyboard, parse_mode="HTML")

        if anonymous:
            await message.reply("Спасибо! Ваше анонимное сообщение отправлено на модерацию.")
        else:
            await message.reply("Спасибо! Сообщение отправлено на модерацию.")
    except Exception as e:
        logger.error(f"Ошибка обработки отправки: {e}")
        await message.reply("Произошла ошибка при отправке сообщения на модерацию.")