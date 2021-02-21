import logging

from aiogram import types
from aiogram.utils import exceptions, markdown
from aiogram.dispatcher import Dispatcher, FSMContext, filters

logger = logging.getLogger(__name__)


def get_main_menu_rkb() -> types.ReplyKeyboardMarkup:
    rkb = types.ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    menu = [
        "Make poster",
        "Manage colors",
    ]
    rkb.add(*(types.KeyboardButton(text) for text in menu))
    return rkb


async def cmd_start(message: types.Message):
    rkb = get_main_menu_rkb()

    await message.answer(
        "Hi there!\n"
        "I can create map posters.\n"
        "Please choose something from menu below\n\n"
        f"{markdown.hitalic('Render process takes a lot of time. Each poster takes about 5 minutes and 10GB RAM.')}",
        reply_markup=rkb,
    )


async def cancel_state(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()

    rkb = get_main_menu_rkb()
    await message.reply(
        "Cancelled.\n"
        "Please choose something from menu below",
        reply_markup=rkb
    )


async def errors_handler(update: types.Update, exception: Exception):
    try:
        raise exception
    except exceptions.MessageNotModified as e:
        logger.warning(f"{e}")
    except Exception as e:
        logger.exception(e, exc_info=True)

    return True


def register_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=["start", "help"])
    dp.register_message_handler(
        cancel_state,
        state='*',
        commands=["cancel"],
    )
    dp.register_message_handler(
        cancel_state,
        filters.Text(equals='cancel', ignore_case=True),
        state='*',
    )
    dp.register_errors_handler(errors_handler)
