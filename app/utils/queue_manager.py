import asyncio
import logging

from app.utils.tg_client_api import send_file
from app.utils.executor import run_blocking
from app.utils.image import make_preview

logger = logging.getLogger("utils - queue_manager")


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
            await callback.message.reply(
                "Your poster is processing now",
                disable_notification=True,
            )

            ret_code = await self.run(cmd)
            self.q.task_done()

            preview_filename = await run_blocking(make_preview, task["output_filename"])

            # TODO: fix bug: sometimes default geojson is deleted!
            # if task["delete_geojson"]:
            #     os.remove(gjf)

            try:
                await asyncio.create_task(send_file(
                    callback.from_user.id,
                    task["output_filename"],
                    preview_filename,
                    task["caption"]
                ))
            except Exception as e:
                logger.error(e)

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
