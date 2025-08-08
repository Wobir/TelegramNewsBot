import logging
from datetime import datetime
from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from db import db
from config import CHANNEL_ID, OWNER_ID
from utils.state import state_manager
from utils.helpers import send_to_channel

logger = logging.getLogger(__name__)

def register_moderation_handlers(dp: Dispatcher, bot):
    @dp.callback_query()
    async def callback(callback_query: CallbackQuery):
        try:
            if callback_query.from_user.id != OWNER_ID:
                await callback_query.answer("Нет доступа", show_alert=True)
                return

            try:
                action, msg_id_str = callback_query.data.split(":")
                msg_id = int(msg_id_str)
                data = state_manager.ideas_cache.get(msg_id)
                
                if not data:
                    await callback_query.answer("Ошибка или устаревшие данные", show_alert=True)
                    return
            except (ValueError, KeyError) as e:
                logger.error(f"Ошибка разбора callback данных: {e}")
                await callback_query.answer("Ошибка данных", show_alert=True)
                return

            uid = data["user_id"]
            first = data.get("first_name", "")
            last = data.get("last_name", "")
            uname = f"{first} {last}".strip() or data.get("username", "") or "без имени"
            text = data["text"]
            content_type = data["content_type"]
            file_id = data["file_id"]
            anonymous = data.get("anonymous", False)

            mention = f"{uname or 'пользователь'}"

            if action == "approve":
                try:
                    if anonymous:
                        anon_caption = f"Сообщение от Анонимно:\n{text}"
                        if content_type == "album":
                            await bot.send_media_group(CHANNEL_ID, media=file_id)
                            await bot.send_message(CHANNEL_ID, anon_caption, parse_mode="HTML")
                        elif content_type == "text":
                            await bot.send_message(CHANNEL_ID, anon_caption, parse_mode="HTML")
                        else:
                            send_map = {
                                "photo": bot.send_photo,
                                "video": bot.send_video,
                                "audio": bot.send_audio,
                                "voice": bot.send_voice,
                                "document": bot.send_document,
                                "animation": bot.send_animation
                            }
                            send_func = send_map.get(content_type, bot.send_message)
                            if content_type == "text":
                                await send_func(CHANNEL_ID, anon_caption, parse_mode="HTML")
                            elif file_id:
                                await send_func(CHANNEL_ID, file_id, caption=anon_caption, parse_mode="HTML")
                    else:
                        if content_type == "album":
                            await bot.send_media_group(CHANNEL_ID, media=file_id)
                            await bot.send_message(CHANNEL_ID, f"Сообщение от {mention}:\n{text}", parse_mode="HTML")
                        else:
                            await send_to_channel(bot, content_type, file_id, text, mention)
                    
                    await callback_query.message.edit_reply_markup()
                    await callback_query.answer("Опубликовано ✅")
                except Exception as e:
                    logger.error(f"Ошибка публикации: {e}")
                    await callback_query.answer("Ошибка публикации", show_alert=True)

            elif action == "idea":
                try:
                    if db.save_idea(uid, uname, text, datetime.now().isoformat()):
                        await callback_query.message.edit_reply_markup()
                        await callback_query.answer("Сохранено в базу 💡")
                    else:
                        await callback_query.answer("Ошибка сохранения", show_alert=True)
                except Exception as e:
                    logger.error(f"Ошибка сохранения идеи: {e}")
                    await callback_query.answer("Ошибка сохранения", show_alert=True)

            elif action == "reject":
                try:
                    await callback_query.message.edit_reply_markup()
                    await callback_query.answer("Отклонено 🚫")
                except Exception as e:
                    logger.error(f"Ошибка отклонения: {e}")

            # Удаляем данные из кэша после обработки
            state_manager.ideas_cache.pop(msg_id, None)
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")
            try:
                await callback_query.answer("Внутренняя ошибка", show_alert=True)
            except:
                pass