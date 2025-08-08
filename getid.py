import asyncio
import logging
import yaml
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка конфигурации из YAML
try:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logger.error("Файл config.yaml не найден")
    exit(1)
except yaml.YAMLError as e:
    logger.error(f"Ошибка в файле config.yaml: {e}")
    exit(1)

API_TOKEN = config.get("api_token")
OWNER_ID = config.get("owner_id")
CHANNEL_ID = config.get("channel_id")

if not all([API_TOKEN, OWNER_ID, CHANNEL_ID]):
    logger.error("Не все обязательные параметры указаны в config.yaml")
    exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command(commands=["getid"]))
async def get_id(message: types.Message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        await message.answer(f"Ваш user_id: {user_id}\nChat id: {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка в команде /getid: {e}")
        await message.answer("Произошла ошибка при получении ID")

async def main():
    logger.info("Бот getid запущен")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота getid: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот getid остановлен")