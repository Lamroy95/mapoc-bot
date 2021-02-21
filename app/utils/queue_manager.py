import asyncio
import os
import logging

from aiogram import types
from aiogram.utils.markdown import hpre

from app.utils.tg_client_api import PyrogramBot

logger = logging.getLogger(__name__)


async def send_file(chat_id, fp, cap):
    async with PyrogramBot() as pyro_bot:
        await pyro_bot.send_document(
            chat_id=chat_id,
            filepath=fp,
            caption=cap,
        )
    os.remove(fp)


class QueueManager:
    __instance = None

    def __init__(self, max_parallel_tasks=1):
        self.max_parallel_tasks = max_parallel_tasks
        self.q = asyncio.Queue()

        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.worker())

    @classmethod
    def get_instance(cls):
        if not cls.__instance:
            cls.__instance = QueueManager()
        return cls.__instance

    def add_task(self, **kwargs) -> int:
        """
        Add a task to the queue and return it's position.
        """
        self.q.put_nowait(kwargs)
        return self.q.qsize()

    async def worker(self):
        while True:
            task = await self.q.get()
            cmd = task["command"]
            gjf = task["geojson"]
            callback = task["callback"]
            manager = task["manager"]
            await callback.message.answer(
                "Your poster is processing now",
                disable_notification=True,
            )

            # await asyncio.sleep(20)
            ret_code = await self.run(cmd)
            self.q.task_done()

            if task["delete_geojson"]:
                os.remove(gjf)

            try:
                asyncio.create_task(send_file(
                    callback.from_user.id,
                    task["output_filename"],
                    task["caption"]
                ))
            except Exception as e:
                await callback.message.answer(hpre(f"{e}\n\n{e.__cause__}\n\n{e.__traceback__}"))

            # await manager.done()
            # from aiogram_dialog.data import DialogContext
            # DialogContext(manager.proxy, "", None).last_message_id = None

    @staticmethod
    async def run(cmd: str):
        proc = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        if stderr:
            logger.error(f'[stderr]\n{stderr.decode()}')

        return proc.returncode
