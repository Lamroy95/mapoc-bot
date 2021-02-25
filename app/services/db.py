from typing import List
from pathlib import Path

from app.config import FILES_PATH


# TODO: implement db
db = {
    "St. Petersburg": {

    }
}


def get_cities_list(pagination=None) -> List[str]:
    return ["St. Petersburg", "Moscow", "Grozniy", "Tokyo"]


def get_shp_path(city_name: str) -> Path:
    d = {
        "St. Petersburg": FILES_PATH / "shp" / "northwestern-fed-district-latest-free.shp",
        "Grozniy": FILES_PATH / "shp" / "north-caucasus-fed-district-latest-free.shp",
        "Moscow": FILES_PATH / "shp" / "central-fed-district-latest-free.shp",
        "Tokyo": FILES_PATH / "shp" / "kanto-latest-free.shp",
    }
    return d[city_name]

def get_color_schemes() -> List[str]:
    return ["black", "white", "coral", "black&red", "blood&milk"]
