import cv2
import numpy as np
import io
import json
from tempfile import NamedTemporaryFile
from decimal import *
from typing import Tuple

from app.config import FILES_PATH, TMP_PATH

import logging

logger = logging.getLogger(__name__)


def get_area_coords(city: np.ndarray, area: np.ndarray) -> tuple:
    methods = [
        cv2.TM_CCOEFF,
        cv2.TM_CCOEFF_NORMED,
        cv2.TM_CCORR,
        cv2.TM_CCORR_NORMED,
        cv2.TM_SQDIFF,
        cv2.TM_SQDIFF_NORMED
    ]
    method = methods[1]
    area_height, area_width, *_ = area.shape

    best_val = None
    top_left = None
    for scale in np.linspace(0.2, 1.0, 20):
        resized = cv2.resize(area, (int(area_width * scale), int(area_height * scale)))

        if (resized.shape[0] < 10 or resized.shape[1] < 10 or
                city.shape[0] < resized.shape[0] or city.shape[0] < resized.shape[0]):
            break

        res = cv2.matchTemplate(city, resized, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            threshold = 0.1
            best_val = threshold
            found_val = min_val
            if found_val < best_val:
                best_val = found_val
                top_left = min_loc
                found_height, found_width, *_ = resized.shape
            if found_val <= threshold:
                break

        else:
            threshold = 0.9
            best_val = 0.3
            found_val = max_val
            if found_val > best_val:
                best_val = found_val
                top_left = max_loc
                found_height, found_width, *_ = resized.shape
            if found_val >= threshold:
                break

    if top_left is None:
        raise ValueError("Area not found")

    bottom_right = (top_left[0] + found_width, top_left[1] + found_height)
    logger.info(f"Best match: {best_val}")

    return top_left, bottom_right


def get_polygon_coords_from_gj(geojson: dict) -> list:
    features: list = geojson.get("features")

    if not features:
        raise ValueError(f"Features not found in GeoJSON")

    if len(features) > 1:
        logger.warning(f"Found {len(features)} features. Be use first")

    first_feature = features[0]
    if not first_feature.get("type") == "Feature":
        raise ValueError(f"Invalid feature type {first_feature.get('type')}. Expected 'Feature'")

    geometry: dict = first_feature.get("geometry")
    if not geometry.get('type') == "Polygon":
        raise ValueError(f"Invalid geometry type {first_feature.get('type')}. Expected 'Polygon'")

    coordinates: list = geometry.get("coordinates")
    if not coordinates:
        raise ValueError(f"Coordinates not found. Check GeoJSON")

    if len(coordinates) > 1:
        logger.warning(f"Found {len(coordinates)} polygons. Be use first")

    first_coords, *_ = coordinates
    return first_coords


def get_area_polygon_coords(cf: list, city_w_h: tuple, area_coords: tuple) -> list:
    # floats to Decimal
    c = [list(map(Decimal, n)) for n in cf]
    w, h = list(map(Decimal, city_w_h))
    area_coords = [list(map(Decimal, n)) for n in area_coords]

    (a_x, a_y), (b_x, b_y) = area_coords

    n00 = c[0][0] + (c[2][0] - c[0][0]) * a_x / w
    n01 = c[0][1] + (c[2][1] - c[0][1]) * (h - b_y) / h
    n20 = c[0][0] + (c[2][0] - c[0][0]) * b_x / w
    n21 = c[0][1] + (c[2][1] - c[0][1]) * (h - a_y) / h

    area_polygon_coords = [
        [n00, n01],
        [n20, n01],
        [n20, n21],
        [n00, n21],
        [n00, n01],
    ]
    return area_polygon_coords


def set_polygon_coords_to_gj(geojson: dict, polygon_coords: list) -> dict:
    geojson["features"][0]["geometry"]["coordinates"][0] = polygon_coords
    return geojson


def area_to_geojson(city_name: str, area_img_bytes: io.BytesIO) -> (str, bytes):
    city_geojson_path = FILES_PATH / "geojson" / (city_name + ".geojson")
    city_image_path = FILES_PATH / "img" / (city_name + ".png")

    city_img = cv2.imread(str(city_image_path), cv2.IMREAD_COLOR)
    area_img = cv2.imdecode(np.frombuffer(area_img_bytes.read(), dtype=np.uint8), cv2.IMREAD_COLOR)

    city_height, city_width, *_ = city_img.shape
    area_top_left, area_bottom_right = get_area_coords(city_img, area_img)

    cv2.rectangle(city_img, area_top_left, area_bottom_right, (0, 0, 255), 2)
    res, selected_buf = cv2.imencode('.png', city_img)
    selected_img_bytes = io.BytesIO(selected_buf)

    with open(city_geojson_path) as gjf:
        city_geojson = json.load(gjf)

    city_polygon_coords = get_polygon_coords_from_gj(city_geojson)
    area_polygon_coords = get_area_polygon_coords(
        city_polygon_coords,
        (city_width, city_height),
        (area_top_left, area_bottom_right)
    )
    area_geojson = set_polygon_coords_to_gj(city_geojson, area_polygon_coords)

    with NamedTemporaryFile(mode="w", dir=TMP_PATH, delete=False) as gjf:
        json.dump(area_geojson, gjf, default=lambda x: float(x) if isinstance(x, Decimal) else str(x))
        area_geojson_path = gjf.name

    return area_geojson_path, selected_img_bytes


if __name__ == '__main__':
    fp = FILES_PATH / "img" / "St. Petersburg.png"
