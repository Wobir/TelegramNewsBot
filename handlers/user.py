from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from time import time
from config import OWNER_ID, MEDIA_TIMEOUT
from db import is_blocked
from utils.state import ideas_cache, user_last_media, media_groups, media_group_tasks
from utils.helpers import process_submission
from utils.media import handle_album_later

from asyncio import create_task


def register_user_handlers(dp: Dispatcher, bot):

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        text = (
            "Привет! Отправляй текст или медиа в бот — они попадут на модерацию.\n"
            "Чтобы отправить анонимно, используй команду /anon + сообщение или медиа.\n"
            "Владелец решит, публиковать ли твоё сообщение.\n"
            "Пожалуйста, не нарушай правила и уважай других."
        )
        await message.reply(text)

    @dp.message(Command("anon"))
    async def cmd_anon(message: Message):
        user_id = message.from_user.id
        username = message.from_user.username

        if is_blocked(user_id):
            await message.reply("Вы заблокированы.")
            return

        text = (message.caption or message.text or "").strip()
        ctype = message.content_type
        file_id = None

        extractors = {
            "photo": lambda m: m.photo[-1].file_id,
            "video": lambda m: m.video.file_id,
            "audio": lambda m: m.audio.file_id,
            "voice": lambda m: m.voice.file_id,
            "document": lambda m: m.document.file_id,
            "animation": lambda m: m.animation.file_id
        }

        if ctype in extractors:
            file_id = extractors[ctype](message)
        elif ctype != "text":
            return await message.reply("Пожалуйста, отправьте текст или поддерживаемое медиа с /anon.")

        msg_id = message.message_id
        ideas_cache[msg_id] = {
            "user_id": user_id,
            "username": username,
            "text": text,
            "content_type": ctype,
            "file_id": file_id,
            "anonymous": True
        }

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve:{msg_id}")],
            [InlineKeyboardButton(text="💡 В базу идей", callback_data=f"idea:{msg_id}")],
            [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"reject:{msg_id}")]
        ])

        mention = f"<b>Анонимное сообщение от @{username or 'без ника'} (ID: {user_id}):</b>\n\n{text}"

        if ctype == "text":
            await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
        else:
            await bot.send_message(OWNER_ID, mention, reply_markup=keyboard)
            await getattr(bot, f"send_{ctype}")(OWNER_ID, file_id, caption=mention, reply_markup=keyboard)

        await message.reply("Спасибо! Ваше анонимное сообщение отправлено на модерацию.")

    @dp.message(Command("clear"))
    async def cmd_clear(message: Message):
        if message.chat.type != "private":
            return await message.reply("Команда работает только в личке.")
        await message.reply("Начинаю очистку чата...")
        for msg_id in range(message.message_id, message.message_id - 100, -1):
            try:
                await bot.delete_message(message.chat.id, msg_id)
            except:
                continue

    @dp.message()
    async def handle(message: Message):
        user_id = message.from_user.id
        username = message.from_user.username
        now = time()
        text = (message.caption or message.text or "").strip()
        ctype = message.content_type

        if is_blocked(user_id):
            return await message.reply("Вы заблокированы.")

        if message.media_group_id:
            gid = message.media_group_id
            media_entry = {"file_id": None, "type": ctype, "caption": text if not media_groups[gid] else None}
            if ctype == "photo":
                media_entry["file_id"] = message.photo[-1].file_id
            elif ctype == "video":
                media_entry["file_id"] = message.video.file_id
            else:
                return await message.reply("Поддерживаются только фото и видео в альбомах.")

            media_groups[gid].append(media_entry)
            if gid not in media_group_tasks:
                media_group_tasks[gid] = create_task(handle_album_later(bot, message, gid, user_id, username))
            return

        extractors = {
            "photo": lambda m: m.photo[-1].file_id,
            "video": lambda m: m.video.file_id,
            "audio": lambda m: m.audio.file_id,
            "voice": lambda m: m.voice.file_id,
            "document": lambda m: m.document.file_id,
            "animation": lambda m: m.animation.file_id
        }

        if ctype in extractors:
            file_id = extractors[ctype](message)
            user_last_media[user_id] = {"file_id": file_id, "type": ctype, "time": now, "text": text}
            if text:
                await process_submission(bot, message, user_id, username, text, ctype, file_id)
                user_last_media.pop(user_id, None)
            else:
                await message.reply("Теперь отправь подпись или текст к медиа.")
            return

        if ctype == "text":
            last = user_last_media.get(user_id)
            if last and now - last["time"] < MEDIA_TIMEOUT:
                await process_submission(bot, message, user_id, username, text, last["type"], last["file_id"])
                user_last_media.pop(user_id, None)
            else:
                await process_submission(bot, message, user_id, username, text, "text", None)
            return

        await message.reply("Пожалуйста, отправьте текст или медиа.")
