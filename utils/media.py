import asyncio
import logging
from typing import List, Tuple, Dict, Any
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.state import state_manager
from config import OWNER_ID

logger = logging.getLogger(__name__)

def build_album(media_list: List[Dict[str, Any]]) -> Tuple[str, List]:
    """Создание альбома из списка медиа"""
    if not media_list:
        return "", []
    
    caption = media_list[0].get("caption", "") or ""
    input_media = []
    
    for i, media_item in enumerate(media_list):
        file_id = media_item.get("file_id")
        media_type = media_item.get("type")
        
        if not file_id or not media_type:
            continue
            
        if media_type == "photo":
            input_media.append(
                InputMediaPhoto(
                    media=file_id, 
                    caption=caption if i == 0 else None, 
                    parse_mode="HTML"
                )
            )
        elif media_type == "video":
            input_media.append(
                InputMediaVideo(
                    media=file_id, 
                    caption=caption if i == 0 else None, 
                    parse_mode="HTML"
                )
            )
    
    return caption, input_media

async def handle_album_later(bot, message: Message, group_id: str, user_id: int, username: str) -> None:
    """Обработка альбома с задержкой"""
    try:
        await asyncio.sleep(2)
        
        media_list = state_manager.media_groups.pop(group_id, [])
        state_manager.media_group_tasks.pop(group_id, None)

        if not media_list:
            return

        caption, input_media = build_album(media_list)
        if not input_media:
            return

        message_id = message.message_id
        state_manager.ideas_cache[message_id] = {
            "user_id": user_id,
            "username": username,
            "text": caption,
            "content_type": "album",
            "file_id": input_media,
            "timestamp": asyncio.get_event_loop().time()
        }

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{message_id}")],
            [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{message_id}")],
            [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{message_id}")],
            [InlineKeyboardButton(text="👤 Анонимно в канал", callback_data=f"anonymous:{message_id}")]
        ])

        await bot.send_media_group(OWNER_ID, media=input_media)
        await bot.send_message(
            OWNER_ID, 
            f"<b>Альбом от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{caption}", 
            reply_markup=keyboard
        )
        await message.reply("Спасибо! Альбом отправлен на модерацию.")
        
    except Exception as e:
        logger.error(f"Ошибка обработки альбома: {e}")
        await message.reply("Произошла ошибка при обработке альбома.")