import os
from pyrogram import Client

from app.config import API_TOKEN, API_ID, API_HASH


class PyrogramBot:
    def __init__(self):
        self._bot = Client(
            "pyro_bot_session",
            bot_token=API_TOKEN,
            no_updates=True,
            api_id=API_ID,
            api_hash=API_HASH,
        )

    async def send_document(self, chat_id, file, caption=None):
        async with self._bot:
            await self._bot.send_document(chat_id=chat_id, document=file, caption=caption)

    async def send_photo(self, chat_id, file, caption=None):
        async with self._bot:
            await self._bot.send_photo(chat_id=chat_id, photo=file, caption=caption)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def send_file(chat_id, fp, preview_fp, cap):
    async with PyrogramBot() as pyro_bot:
        await pyro_bot.send_photo(
            chat_id=chat_id,
            file=preview_fp,
            caption=f"{cap} (preview)",
        )
        await pyro_bot.send_document(
            chat_id=chat_id,
            file=fp,
            caption=cap,
        )
    os.remove(fp)
    os.remove(preview_fp)
