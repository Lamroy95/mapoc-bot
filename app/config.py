from os import environ
from pathlib import Path
from dotenv import load_dotenv


load_dotenv(verbose=True)

API_TOKEN = environ.get("API_TOKEN")

CMD_TEMPLATE = "mapoc poster create --shp_path {shp} --geojson {geojson} --colors {colors} --output_prefix {prefix}"

BASE_DIR = Path(__file__).resolve().parent
FILES_PATH = BASE_DIR / "files"
TMP_PATH = FILES_PATH / "tmp"
