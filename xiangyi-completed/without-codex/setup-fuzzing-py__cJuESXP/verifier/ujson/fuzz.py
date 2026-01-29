import sys

import atheris
import ujson


_MAX_TEXT = 2048


def _make_obj(fdp: atheris.FuzzedDataProvider, depth: int = 0):
    if depth > 3:
        return fdp.ConsumeIntInRange(-10**6, 10**6)

    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.ConsumeIntInRange(-10**6, 10**6)
    if choice == 1:
        return fdp.ConsumeBool()
    if choice == 2:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 3:
        return [
            _make_obj(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 6))
        ]
    key = fdp.ConsumeUnicodeNoSurrogates(16)
    return {key: _make_obj(fdp, depth + 1)}


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(min(_MAX_TEXT, fdp.remaining_bytes()))
    blob = fdp.ConsumeBytes(min(1024, fdp.remaining_bytes()))

    if text:
        try:
            ujson.loads(text)
        except Exception:
            pass
        try:
            ujson.decode(text)
        except Exception:
            pass

    if blob:
        try:
            ujson.loads(blob)
        except Exception:
            pass
        try:
            ujson.decode(blob)
        except Exception:
            pass

    obj = _make_obj(fdp)
    try:
        ujson.dumps(
            obj,
            ensure_ascii=fdp.ConsumeBool(),
            encode_html_chars=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
            sort_keys=fdp.ConsumeBool(),
            indent=fdp.ConsumeIntInRange(0, 4),
            allow_nan=fdp.ConsumeBool(),
            reject_bytes=fdp.ConsumeBool(),
        )
    except Exception:
        pass

    try:
        ujson.encode(obj)
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
