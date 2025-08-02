import asyncio
import yaml
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Загрузка конфигурации из YAML
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

API_TOKEN = config["api_token"]
OWNER_ID = config["owner_id"]
CHANNEL_ID = config["channel_id"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command(commands=["getid"]))
async def get_id(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    await message.answer(f"Ваш user_id: {user_id}\nChat id: {chat_id}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
