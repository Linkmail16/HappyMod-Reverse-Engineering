import json
import requests

from decode import decode_response
from app_search import _UID, _VERSION, _LANG, make_stamp
from genhash import generate_hash

DOWNLOAD_BASE = "https://d.apkomega.com/202101/api"

_COUNTRY = "US"
_CHANNEL = "happymod"
_AID = "98pyooirb6mad326"


def get_apk_download(url_id: str, refer: str) -> dict:
    payload = {
        "version": _VERSION,
        "uid": _UID,
        "stamp": make_stamp(),
        "country": _COUNTRY,
        "lang": _LANG,
        "hash": generate_hash(url_id),
        "url_id": url_id,
        "refer": refer,
        "aid": _AID,
        "get_hpt": 0,
        "channel": _CHANNEL,
        "username": "",
    }
    resp = requests.post(
        f"{DOWNLOAD_BASE}/get_apk_download_v2.php", data=payload, timeout=15
    )
    resp.raise_for_status()
    return json.loads(decode_response(resp.text.strip()))
