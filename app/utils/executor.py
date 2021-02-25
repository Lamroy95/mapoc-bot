import asyncio
import concurrent.futures


pp_executor = concurrent.futures.ProcessPoolExecutor(4)


async def run_blocking(func, *args):
    return await asyncio.get_event_loop().run_in_executor(pp_executor, func, *args)
