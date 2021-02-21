import logging
import time


def log_processing(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        logger = logging.getLogger(__name__)
        logger.info(f"Processing {func.__name__}...")
        value = func(*args, **kwargs)
        logger.info(
            f"Finished processing {func.__name__} in {time.time() - start}s"
        )
        return value

    return wrapper
