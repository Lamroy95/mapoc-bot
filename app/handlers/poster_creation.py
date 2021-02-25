import logging

from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram_dialog import DialogManager

from app.states import PosterCreation
from app.utils.queue_manager import QueueManager


logger = logging.getLogger("handlers - poster_creation")


async def poster_create_start(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(PosterCreation.city, reset_stack=True)


async def in_queue_handler(message: types.Message, dialog_manager: DialogManager):
    await message.reply("Wait until your poster is done")


async def qsize_handler(message: types.Message, dialog_manager: DialogManager):
    qm = QueueManager.get_instance()
    await message.reply(f"Queue size: {qm.q.qsize()}")


def register_poster_creation(dp: Dispatcher):
    dp.register_message_handler(in_queue_handler, state=PosterCreation.confirmation)
    dp.register_message_handler(poster_create_start, text="Make poster", state="*")
    dp.register_message_handler(qsize_handler, commands=["qsize"], state="*")
