import hashlib


def generate_hash(url_id: str) -> str:

    full_md5 = hashlib.md5((url_id + "android_require_apk").encode()).hexdigest()

    return full_md5[10:14] + full_md5[25:29] + full_md5[18:22] + full_md5[5:9]
