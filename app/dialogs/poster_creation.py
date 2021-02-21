from io import BytesIO
import time
import logging

from aiogram import types
from aiogram.utils import markdown

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets import text
from aiogram_dialog.widgets import kbd

from app.states import PosterCreation
from app.config import FILES_PATH, CMD_TEMPLATE
from app.utils.coords import area_to_geojson
from app.utils.queue_manager import QueueManager
from app.services import db

logger = logging.getLogger(__name__)


async def set_selected_city(c: types.CallbackQuery, item_id: str, select: kbd.Select, manager: DialogManager):
    city_name = item_id
    manager.context.set_data("city", city_name)


async def city_name_getter(dialog_manager: DialogManager, **kwargs):
    city = dialog_manager.context.data("city")
    return {
        "city_name": city,
    }


async def collected_data_getter(dialog_manager: DialogManager, **kwargs):
    city = dialog_manager.context.data("city")
    area = dialog_manager.context.data("is_area_specified", False)
    color = dialog_manager.context.data("color")
    return {
        "city_name": city,
        "is_area_specified": area,
        "color": color,
    }


async def send_city_map(c: types.CallbackQuery, button: kbd.Button, manager: DialogManager):
    city_name = manager.context.data("city")
    city_img_path = FILES_PATH / "img" / (city_name + ".png")
    await c.message.answer_photo(
        types.InputFile(city_img_path),
        caption=f"Save this image, crop the area that you need and {markdown.hbold('send cropped image back')}"
    )


async def area_image_handler(m: types.Message, dialog: Dialog, manager: DialogManager):
    city_select: kbd.Select = manager.dialog().find("city_select")
    city_name = city_select.get_checked(manager)

    if not m.photo:
        geojson_path = get_city_gjs_path(city_name)
        manager.context.set_data("geojson", geojson_path)
        await m.reply("There's no photo in your message.\nSkipping.")
        await dialog.next(manager)
        return

    manager.context.set_data("is_area_specified", True)
    area_img = BytesIO()
    await m.photo[-1].download(area_img, seek=True)

    # try:
    #     geojson_path = area_to_geojson(city_name, area_img)
    # except ValueError as e:
    #     geojson_path = get_city_gjs_path(city_name)

    geojson_path, selected_image_bytes = area_to_geojson(city_name, area_img)
    manager.context.set_data("geojson", geojson_path)
    await m.reply_photo(types.InputFile(selected_image_bytes), caption="Defined area")

    await dialog.next(manager)


def get_city_gjs_path(city_name):
    gjs_path = FILES_PATH / "geojson" / (city_name + ".geojson")
    return gjs_path


async def set_city_geojson(c: types.CallbackQuery, button: kbd.Button, manager: DialogManager):
    city_select: kbd.Select = manager.dialog().find("city_select")
    city_name = city_select.get_checked(manager)
    geojson_path = get_city_gjs_path(city_name)
    manager.context.set_data("geojson", geojson_path)
    await manager.dialog().next(manager)


async def set_selected_color(c: types.CallbackQuery, item_id: str, select: kbd.Select, manager: DialogManager):
    color_scheme_name = item_id
    manager.context.set_data("color", color_scheme_name)


async def make_poster(c: types.CallbackQuery, button: kbd.Button, manager: DialogManager):
    city = manager.context.data("city")
    gjf = manager.context.data("geojson")
    shp = db.get_shp_path(city)
    color = manager.context.data("color")
    prefix = f"{c.from_user.id}_{time.time():.0f}_{''.join(city.split())}"
    cmd = CMD_TEMPLATE.format(shp=shp, geojson=gjf, colors=color, prefix=prefix)

    qm = QueueManager.get_instance()
    pos = qm.add_task(
        callback=c,
        manager=manager,
        command=cmd,
        geojson=gjf,
        output_filename=f"{prefix}_{color}.png",
        delete_geojson=manager.context.data("is_area_specified", False),
    )

    manager.context.set_data("pending", True)
    await c.message.answer(
        f"Your position in queue: {markdown.hbold(pos)}\n"
        f"Cmd: {markdown.hbold(cmd)}"
    )

    # TODO: remove this
    await manager.done()
    from aiogram_dialog.data import DialogContext
    DialogContext(manager.proxy, "", None).last_message_id = None


city_window = Window(
    text=text.Const("Let's start.\nChoose city"),
    kbd=kbd.Group(
        kbd.Radio(
            checked_text=text.Format("✅ {item}"), unchecked_text=text.Format("{item}"),
            items=db.get_cities_list(),
            item_id_getter=lambda x: x,
            id="city_select",
            on_state_changed=set_selected_city,
        ),
        kbd.Next(
            when=lambda d, w, m: m.dialog().find("city_select").get_checked(m) is not None,
        ),
    ),
    state=PosterCreation.city,
)

area_choice_window = Window(
    text=text.Format(
        "Chosen city: {city_name}\n"
        "Would you like to specify city area?"
    ),
    kbd=kbd.Group(
            kbd.Row(
                kbd.Button(text.Const("Yes"), id="area_yes", on_click=send_city_map),
                kbd.Button(text.Const("No"), id="area_no", on_click=set_city_geojson),
            ),
            kbd.Back(),
    ),
    getter=city_name_getter,
    state=PosterCreation.city_area,
    on_message=area_image_handler,
)

color_choice_window = Window(
    text=text.Const("Good. Now choose color scheme:"),
    kbd=kbd.Group(
        kbd.Radio(
            checked_text=text.Format("✅ {item}"), unchecked_text=text.Format("{item}"),
            items=db.get_color_schemes(),
            item_id_getter=lambda x: x,
            id="color_select",
            on_state_changed=set_selected_color,
        ),
        kbd.Row(
            kbd.Back(),
            kbd.Next(
                when=lambda d, w, m: m.dialog().find("color_select").get_checked(m) is not None,
            ),
        ),
    ),
    state=PosterCreation.color_scheme,
)

summary_window = Window(
    text=text.Format(
        "City: <b>{city_name}</b>\n"
        "Specified area: <b>{is_area_specified}</b>\n"
        "Color scheme: <b>{color}</b>"
    ),
    kbd=kbd.Group(
        kbd.Button(text.Const("Create"), id="poster_confirm", on_click=make_poster),
        kbd.Row(
            kbd.Back(), kbd.Cancel()
        ),
    ),
    getter=collected_data_getter,
    state=PosterCreation.confirmation,
)

dialog = Dialog(
    city_window,
    area_choice_window,
    color_choice_window,
    summary_window,
)
