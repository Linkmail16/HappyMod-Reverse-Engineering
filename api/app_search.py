import hashlib
import json
import time
import requests

from decode import decode_response
from happymodUid import random_uid

BASE_URL = "https://app.apkomega.com/202010/api"

_VERSION = "3.2.6"
_LANG = "es"
_COUNTRY = "CO"
_STAMP_KEY = "this_is_happymod"

_UID = random_uid()
_server_time_offset: int | None = None


def generate_uid(
    board: str,
    brand: str,
    device: str,
    display: str,
    host: str,
    build_id: str,
    manufacturer: str,
    model: str,
    product: str,
    tags: str,
    type_: str,
    user: str,
    gaid: str,
) -> str:
    prefix = "35"
    for field in [
        board,
        brand,
        device,
        display,
        host,
        build_id,
        manufacturer,
        model,
        product,
        tags,
        type_,
        user,
    ]:
        prefix += str(len(field) % 10)
    return hashlib.md5((prefix + gaid).encode()).hexdigest()


def _get_server_offset() -> int:
    global _server_time_offset
    if _server_time_offset is not None:
        return _server_time_offset
    try:
        resp = requests.post(
            f"{BASE_URL}/server_time.php",
            data={"version": _VERSION, "uid": _UID, "country": _COUNTRY},
            timeout=10,
        )
        data = json.loads(decode_response(resp.text.strip()))
        if data.get("status") == 1:
            _server_time_offset = int(time.time()) - data["timestamp"]
            return _server_time_offset
    except Exception:
        pass
    _server_time_offset = 0
    return 0


def make_stamp() -> str:
    offset = _get_server_offset()
    time_str = str(int(time.time()) - offset)
    raw = _UID + time_str + _STAMP_KEY
    return hashlib.md5(raw.encode()).hexdigest()


def search_apps(keywords: str, page: int = 1) -> dict:
    payload = {
        "version": _VERSION,
        "uid": _UID,
        "stamp": make_stamp(),
        "page": page,
        "keywords": keywords,
        "lang": _LANG,
        "is_new_user": 1,
        "is_input": 2,
        "input_word": keywords[:3],
    }
    resp = requests.post(f"{BASE_URL}/search_list.php", data=payload, timeout=15)
    resp.raise_for_status()
    return json.loads(decode_response(resp.text.strip()))
