import hashlib
import requests
import time


def get_server_time() -> int:
    """Replica C8845a.m23269v0() — el offset guardado tras llamar a server_time.php"""
    try:
        r = requests.post(
            "https://app.apkomega.com/202010/api/server_time.php",
            data={"version": "3.2.6", "uid": uid, "country": "CO"},
        )

        body = decode_response(r.text)
        import json

        data = json.loads(body)
        if data.get("status") == 1:
            server_ts = data["timestamp"]
            offset = (int(time.time())) - server_ts
            return offset
    except:
        pass
    return 0


def get_time_str(offset: int) -> str:
    """Replica C0060b.m256b()"""
    return str(int(time.time()) - offset)


def get_stamp(time_str: str, uid: str) -> str:
    """Replica NativeHelper.getStamp()"""
    key = "this_is_happymod"
    raw = uid + time_str + key
    return hashlib.md5(raw.encode()).hexdigest()


import base64, gzip


def decode_response(raw: str) -> str:
    result = []
    for i, ch in enumerate(raw):
        code = ord(ch)
        if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122):
            shifted = code - (i % 10)
            if shifted < 48:
                code = 122 - (48 - shifted) + 1
            elif code < 65 or shifted >= 65:
                if code < 97 or shifted >= 97:
                    code = shifted
                else:
                    code = (90 - (97 - shifted)) + 1
            else:
                code = (57 - (65 - shifted)) + 1
        result.append(chr(code))
    decoded = base64.b64decode("".join(result) + "==")
    if decoded[:2] == b"\x1f\x8b":
        decoded = gzip.decompress(decoded)
    return decoded.decode("utf-8")


def search(keyword: str, uid: str, page: int = 1):
    offset = get_server_time()
    time_str = get_time_str(offset)
    stamp = get_stamp(time_str, uid)

    r = requests.post(
        "https://app.apkomega.com/202010/api/search_list.php",
        data={
            "version": "3.2.6",
            "uid": uid,
            "stamp": stamp,
            "page": page,
            "keywords": keyword,
            "lang": "es",
            "is_new_user": "1",
            "is_input": "2",
            "input_word": keyword[:3],
        },
    )
    return decode_response(r.text)


uid = "68920e5674b1d3ec969e4637d31e0345"
import json

result = search("whatsapp", uid)
print(json.dumps(json.loads(result), indent=2))
