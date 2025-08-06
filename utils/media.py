from asyncio import sleep
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.state import ideas_cache, media_groups, media_group_tasks
from config import OWNER_ID

def build_album(media_list):
    caption = media_list[0].get("caption") or ""
    input_media = [
        InputMediaPhoto(media=m["file_id"], caption=caption if i == 0 else None, parse_mode="HTML")
        if m["type"] == "photo"
        else InputMediaVideo(media=m["file_id"], caption=caption if i == 0 else None, parse_mode="HTML")
        for i, m in enumerate(media_list)
    ]
    return caption, input_media

async def handle_album_later(bot, message: Message, group_id: str, user_id: int, username: str):
    await sleep(2)
    media_list = media_groups.pop(group_id, [])
    media_group_tasks.pop(group_id, None)

    if not media_list:
        return

    caption, input_media = build_album(media_list)
    message_id = message.message_id
    ideas_cache[message_id] = {
        "user_id": user_id,
        "username": username,
        "text": caption,
        "content_type": "album",
        "file_id": input_media
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{message_id}")],
        [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{message_id}")],
        [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{message_id}")],
        [InlineKeyboardButton(text="👤 Анонимно в канал", callback_data=f"anonymous:{message_id}")]
    ])

    await bot.send_media_group(OWNER_ID, media=input_media)
    await bot.send_message(OWNER_ID, f"<b>Альбом от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{caption}", reply_markup=keyboard)
    await message.reply("Спасибо! Альбом отправлен на модерацию.")
