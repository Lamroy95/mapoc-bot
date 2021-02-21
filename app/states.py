from aiogram.dispatcher.filters.state import State, StatesGroup


class PosterCreation(StatesGroup):
    city = State()
    city_area = State()
    color_scheme = State()
    confirmation = State()
    pending = State()


class ColorSchemeAdding(StatesGroup):
    face_color = State()
    water_color = State()
    greens_color = State()
    roads_color = State()
    name = State()
