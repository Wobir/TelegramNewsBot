import asyncio
import logging
import time
from typing import Optional
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, MEDIA_TIMEOUT
from db import db
from utils.state import state_manager
from utils.helpers import process_submission
from utils.media import handle_album_later

logger = logging.getLogger(__name__)

def register_user_handlers(dp: Dispatcher, bot):
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        try:
            text = (
                "Привет! Отправляй текст или медиа в бот — они попадут на модерацию.\n"
                "Чтобы отправить анонимно, используй команду /anon + сообщение или медиа.\n"
                "Владелец решит, публиковать ли твоё сообщение.\n"
                "Пожалуйста, не нарушай правила и уважай других."
            )
            await message.reply(text)
        except Exception as e:
            logger.error(f"Ошибка в команде /start: {e}")

    @dp.message(Command("anon"))
    async def cmd_anon(message: Message):
        try:
            user_id = message.from_user.id
            username = message.from_user.username

            if db.is_blocked(user_id):
                await message.reply("Вы заблокированы.")
                return

            # Извлекаем текст из сообщения
            text = ""
            if message.text:
                text = message.text[5:].strip()  # Убираем "/anon"
            elif message.caption:
                text = message.caption.strip()

            content_type = message.content_type
            file_id = None

            # Обработка медиа
            extractors = {
                "photo": lambda m: m.photo[-1].file_id if m.photo else None,
                "video": lambda m: m.video.file_id if m.video else None,
                "audio": lambda m: m.audio.file_id if m.audio else None,
                "voice": lambda m: m.voice.file_id if m.voice else None,
                "document": lambda m: m.document.file_id if m.document else None,
                "animation": lambda m: m.animation.file_id if m.animation else None
            }

            if content_type in extractors:
                file_id = extractors[content_type](message)
                if not file_id:
                    await message.reply("Не удалось получить файл.")
                    return
            elif content_type == "text" and not text:
                await message.reply("Пожалуйста, отправьте текст или медиа с /anon.")
                return

            # Отправляем на модерацию как обычное сообщение, но с флагом анонимности
            await process_submission(bot, message, user_id, username, text, content_type, file_id, anonymous=True)
            
        except Exception as e:
            logger.error(f"Ошибка в команде /anon: {e}")
            await message.reply("Произошла ошибка при обработке анонимного сообщения.")

    @dp.message(Command("clear"))
    async def cmd_clear(message: Message):
        try:
            if message.chat.type != "private":
                await message.reply("Команда работает только в личке.")
                return
            
            await message.reply("Начинаю очистку чата...")
            deleted_count = 0
            
            for msg_id in range(message.message_id, max(0, message.message_id - 100), -1):
                try:
                    await bot.delete_message(message.chat.id, msg_id)
                    deleted_count += 1
                    await asyncio.sleep(0.1)  # Избегаем флуд-контроля
                except Exception:
                    continue
            
            await message.reply(f"Очистка завершена. Удалено сообщений: {deleted_count}")
        except Exception as e:
            logger.error(f"Ошибка в команде /clear: {e}")
            await message.reply("Произошла ошибка при очистке чата.")

    @dp.message()
    async def handle(message: Message):
        try:
            user_id = message.from_user.id
            username = message.from_user.username
            now = time.time()
            text = (message.caption or message.text or "").strip()
            content_type = message.content_type

            if db.is_blocked(user_id):
                await message.reply("Вы заблокированы.")
                return

            if message.media_group_id:
                gid = message.media_group_id
                media_entry = {
                    "file_id": None, 
                    "type": content_type, 
                    "caption": text if not state_manager.media_groups[gid] else None
                }
                
                if content_type == "photo" and message.photo:
                    media_entry["file_id"] = message.photo[-1].file_id
                elif content_type == "video" and message.video:
                    media_entry["file_id"] = message.video.file_id
                else:
                    await message.reply("Поддерживаются только фото и видео в альбомах.")
                    return

                state_manager.media_groups[gid].append(media_entry)
                if gid not in state_manager.media_group_tasks:
                    state_manager.media_group_tasks[gid] = asyncio.create_task(
                        handle_album_later(bot, message, gid, user_id, username)
                    )
                return

            extractors = {
                "photo": lambda m: m.photo[-1].file_id if m.photo else None,
                "video": lambda m: m.video.file_id if m.video else None,
                "audio": lambda m: m.audio.file_id if m.audio else None,
                "voice": lambda m: m.voice.file_id if m.voice else None,
                "document": lambda m: m.document.file_id if m.document else None,
                "animation": lambda m: m.animation.file_id if m.animation else None
            }

            if content_type in extractors:
                file_id = extractors[content_type](message)
                if not file_id:
                    await message.reply("Не удалось получить файл.")
                    return
                    
                state_manager.user_last_media[user_id] = {
                    "file_id": file_id, 
                    "type": content_type, 
                    "time": now, 
                    "text": text
                }
                
                if text:
                    await process_submission(bot, message, user_id, username, text, content_type, file_id)
                    state_manager.user_last_media.pop(user_id, None)
                else:
                    await message.reply("Теперь отправь подпись или текст к медиа.")
                return

            if content_type == "text":
                last = state_manager.user_last_media.get(user_id)
                if last and now - last["time"] < MEDIA_TIMEOUT:
                    await process_submission(bot, message, user_id, username, text, last["type"], last["file_id"])
                    state_manager.user_last_media.pop(user_id, None)
                else:
                    await process_submission(bot, message, user_id, username, text, "text", None)
                return

            await message.reply("Пожалуйста, отправьте текст или медиа.")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await message.reply("Произошла ошибка при обработке сообщения.")