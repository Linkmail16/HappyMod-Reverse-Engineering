import base64
import gzip


def decode_response(raw: str) -> str:
    chars = list(raw)
    result = []

    for i, ch in enumerate(chars):
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

    intermediate = "".join(result)
    decoded_bytes = base64.b64decode(intermediate + "==")

    if decoded_bytes[:2] == b"\x1f\x8b":
        decoded_bytes = gzip.decompress(decoded_bytes)

    return decoded_bytes.decode("utf-8")
