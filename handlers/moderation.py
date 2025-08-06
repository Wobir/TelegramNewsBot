from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from datetime import datetime
from db import save_idea
from config import CHANNEL_ID, OWNER_ID
from utils.state import ideas_cache
from utils.helpers import send_to_channel


def register_moderation_handlers(dp: Dispatcher, bot):

    @dp.callback_query()
    async def callback(callback_query: CallbackQuery):
        if callback_query.from_user.id != OWNER_ID:
            return await callback_query.answer("Нет доступа", show_alert=True)

        try:
            action, msg_id = callback_query.data.split(":")
            msg_id = int(msg_id)
            data = ideas_cache[msg_id]
        except:
            return await callback_query.answer("Ошибка или устаревшие данные", show_alert=True)

        uid = data["user_id"]
        first = data.get("first_name") or ""
        last = data.get("last_name") or ""
        uname = f"{first} {last}".strip() or data.get("username") or "без имени"
        text = data["text"]
        ctype = data["content_type"]
        file_id = data["file_id"]
        anonymous = data.get("anonymous", False)

        mention = f"👤{uname or 'пользователь'}"

        if action == "approve":
            if anonymous:
                anon_caption = f"Сообщение от Анонимно:\n{text}"
                if ctype == "album":
                    await bot.send_media_group(CHANNEL_ID, media=file_id)
                    await bot.send_message(CHANNEL_ID, anon_caption)
                elif ctype == "text":
                    await bot.send_message(CHANNEL_ID, anon_caption)
                else:
                    send_map = {
                        "photo": bot.send_photo,
                        "video": bot.send_video,
                        "audio": bot.send_audio,
                        "voice": bot.send_voice,
                        "document": bot.send_document,
                        "animation": bot.send_animation
                    }
                    await send_map.get(ctype, bot.send_message)(CHANNEL_ID, file_id, caption=anon_caption)
            else:
                if ctype == "album":
                    await bot.send_media_group(CHANNEL_ID, media=file_id)
                    await bot.send_message(CHANNEL_ID, f"Сообщение от {mention}:\n{text}")
                else:
                    await send_to_channel(bot, ctype, file_id, text, mention)

            await callback_query.message.edit_reply_markup()
            return await callback_query.answer("Опубликовано ✅")

        elif action == "idea":
            save_idea(uid, uname, text, datetime.now().isoformat())
            await callback_query.message.edit_reply_markup()
            return await callback_query.answer("Сохранено в базу 💡")

        elif action == "reject":
            await callback_query.message.edit_reply_markup()
            return await callback_query.answer("Отклонено 🚫")
