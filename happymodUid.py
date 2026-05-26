import hashlib
import random
import uuid


def generate_uid(board, brand, device, display, host,
                 build_id, manufacturer, model, product,
                 tags, type_, user, gaid: str) -> str:
    prefix = "35"
    for field in [board, brand, device, display, host,
                  build_id, manufacturer, model, product,
                  tags, type_, user]:
        prefix += str(len(field) % 10)
    return hashlib.md5((prefix + gaid).encode()).hexdigest()

_DEVICES = [
    dict(board="SM8650-AB",   brand="samsung",  manufacturer="samsung",
         model="SM-S918B",    product="dm3q",   device="dm3q",
         display="S918BXXS4CXL4", host="sep-150", build_id="UP1A.231005.007",
         tags="release-keys", type_="user",      user="dpi"),
    dict(board="taro",        brand="samsung",  manufacturer="samsung",
         model="SM-G998B",    product="p3",     device="p3",
         display="G998BXXS5HWB2", host="SWDD8021", build_id="TP1A.220624.014",
         tags="release-keys", type_="user",      user="dpi"),
    dict(board="lahaina",     brand="xiaomi",   manufacturer="Xiaomi",
         model="2201123G",    product="zeus",   device="zeus",
         display="V14.0.2.0.TLACNXM", host="pangu-ota-bdgp10", build_id="SKQ1.211006.001",
         tags="release-keys", type_="user",      user="builder"),
    dict(board="taro",        brand="OnePlus",  manufacturer="OnePlus",
         model="CPH2449",     product="op535al1", device="OP535AL1",
         display="PJD110_13.1.0.591(EX01)", host="builduser", build_id="TP1A.220624.014",
         tags="release-keys", type_="user",      user="root"),
    dict(board="kona",        brand="Asus",     manufacturer="Asus",
         model="ASUS_AI2401_A", product="ASUS_AI2401_A", device="ASUS_AI2401_A",
         display="Asus-user 9.0.0 20171130.276299 release-keys",
         host="dev",          build_id="PI",
         tags="release-keys", type_="user",      user="Asus"),
]


def random_uid() -> str:

    profile = random.choice(_DEVICES)
    gaid = str(uuid.uuid4())
    return generate_uid(**profile, gaid=gaid)

