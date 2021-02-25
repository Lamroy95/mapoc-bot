import cv2
import numpy as np
import io
import json
from tempfile import NamedTemporaryFile
from decimal import *
from numba import njit

from app.config import FILES_PATH, TMP_PATH

import logging

logger = logging.getLogger("utils - coords")


@njit
def filter_scale(s, c_shape, a_shape):
    return s < c_shape[0]/a_shape[0] and s < c_shape[1]/a_shape[1]


@njit
def get_scales(c_shape, a_shape, n=50):
    arr = np.linspace(0.2, 1.0, n)

    j = 0
    for i in range(arr.size):
        if filter_scale(arr[i], c_shape, a_shape):
            j += 1
    result = np.empty(j, dtype=arr.dtype)
    j = 0
    for i in range(arr.size):
        if filter_scale(arr[i], c_shape, a_shape):
            result[j] = arr[i]
            j += 1

    return result


def find_template(city, resized, method=cv2.TM_CCOEFF_NORMED):
    res = cv2.matchTemplate(city, resized, method)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    bottom_right = (max_loc[0] + resized.shape[1], max_loc[1] + resized.shape[0])
    return max_val, *max_loc, *bottom_right


def get_area_coords_fast(city: np.ndarray, area: np.ndarray, n=50) -> tuple:
    area_height = area.shape[0]
    area_width = area.shape[1]

    scales_arr = get_scales(city.shape, area.shape, n)
    resized_imgs = np.array(
        [
            cv2.resize(area, (int(area_width * scale), int(area_height * scale)))
            for scale in scales_arr
        ],
        dtype=object
    )
    matches: np.ndarray = np.array(
        [
            find_template(city, resized)
            for resized
            in resized_imgs
        ],
        dtype=object
    )
    best_match = matches[matches.argmax(axis=0)[0]]

    top_left = best_match[1:3]
    bottom_right = best_match[3:5]

    return tuple(top_left), tuple(bottom_right)


def get_area_coords(city: np.ndarray, area: np.ndarray, n=50) -> tuple:
    area_height, area_width = area.shape[:2]
    method = cv2.TM_CCOEFF_NORMED

    lower_boundary = 0.2
    top_left = None
    for scale in np.linspace(0.1, 1, n):
        resized = cv2.resize(area, (int(area_width * scale), int(area_height * scale)))
        if city.shape[0] <= resized.shape[0] or city.shape[1] <= resized.shape[1]\
                or resized.shape[0] < 10 or resized.shape[1] < 10:
            continue

        res = cv2.matchTemplate(city, resized, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > lower_boundary:
            lower_boundary = max_val
            top_left = max_loc
            res_shape = resized.shape[:2]

    if top_left is None:
        raise ValueError

    bottom_right = (top_left[0] + res_shape[1], top_left[1] + res_shape[0])

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

    # TODO: refactor fast method
    # area_top_left, area_bottom_right = get_area_coords(city_img, area_img)
    area_top_left, area_bottom_right = get_area_coords_fast(city_img, area_img)

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