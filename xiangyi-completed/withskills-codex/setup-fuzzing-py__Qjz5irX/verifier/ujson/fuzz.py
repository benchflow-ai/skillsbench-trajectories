import atheris
import sys

import ujson


def _make_obj(fdp: atheris.FuzzedDataProvider, depth: int):
    if depth <= 0:
        choice = fdp.ConsumeIntInRange(0, 4)
    else:
        choice = fdp.ConsumeIntInRange(0, 6)

    if choice == 0:
        return None
    if choice == 1:
        return fdp.ConsumeBool()
    if choice == 2:
        return fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if choice == 3:
        return fdp.ConsumeFloat()
    if choice == 4:
        length = fdp.ConsumeIntInRange(0, 64)
        return fdp.ConsumeUnicodeNoSurrogates(length)
    if choice == 5:
        size = fdp.ConsumeIntInRange(0, 8)
        return [_make_obj(fdp, depth - 1) for _ in range(size)]
    size = fdp.ConsumeIntInRange(0, 8)
    obj = {}
    for _ in range(size):
        key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
        obj[key] = _make_obj(fdp, depth - 1)
    return obj


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    length = fdp.ConsumeIntInRange(0, 4096)
    raw = fdp.ConsumeBytes(length)
    try:
        ujson.loads(raw)
    except (ValueError, TypeError, OverflowError):
        pass

    try:
        text = raw.decode("utf-8", errors="ignore")
        ujson.loads(text)
    except (ValueError, TypeError, OverflowError):
        pass

    obj = _make_obj(fdp, 3)
    try:
        ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
