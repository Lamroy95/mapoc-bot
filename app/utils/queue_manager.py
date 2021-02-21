import asyncio
import logging

logger = logging.getLogger(__name__)


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
            await callback.message.answer("Your poster is processing now")

            # await asyncio.sleep(20)
            ret_code = self.run(cmd)
            self.q.task_done()

            if task["delete_geojson"]:
                gjf.unlink()

            # send output_filename here
            await callback.message.answer("Poster created!")

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
