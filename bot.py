import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram_dialog import DialogRegistry

from app.config import API_TOKEN
from app.handlers.common import register_common
from app.handlers.poster_creation import register_poster_creation
from app import dialogs
from app.utils.queue_manager import QueueManager


def register_handlers(dp: Dispatcher):
    register_common(dp)
    register_poster_creation(dp)


def register_dialogs(registry: DialogRegistry):
    registry.register(dialogs.poster_creation.dialog)


async def main():
    logger = logging.getLogger("main")
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting mapoc-bot")

    storage = MemoryStorage()
    bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot, storage=storage)
    registry = DialogRegistry(dp)

    register_handlers(dp)
    register_dialogs(registry)

    q_manager = QueueManager()

    try:
        await dp.start_polling()
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
