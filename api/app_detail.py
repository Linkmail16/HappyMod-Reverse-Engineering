import json
import requests

from decode import decode_response

CLIST_BASE = "https://app.happymodapp.com/clist"

_VERSION = "3.2.6"
_LANG = "es"
_COUNTRY = "US"


def get_mod_list(url_id: str, sort: str = "rating", page: int = 1) -> dict:
    path = f"{_VERSION},{_LANG},{_COUNTRY},{page},{url_id},{sort},{page},pdt_mod_list_v3.html"
    resp = requests.get(f"{CLIST_BASE}/{path}", timeout=15)
    resp.raise_for_status()
    return json.loads(decode_response(resp.text.strip()))
