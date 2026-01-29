import sys

import atheris
from atheris import FuzzedDataProvider

import ujson


def _rand_scalar(fdp: FuzzedDataProvider):
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if choice == 1:
        return fdp.ConsumeBool()
    if choice == 2:
        return fdp.ConsumeUnicodeNoSurrogates(32)
    if choice == 3:
        return None
    return fdp.ConsumeBytes(16)


def _rand_object(fdp: FuzzedDataProvider):
    kind = fdp.ConsumeIntInRange(0, 2)
    if kind == 0:
        items = []
        for _ in range(fdp.ConsumeIntInRange(0, 5)):
            items.append(_rand_scalar(fdp))
        return items
    if kind == 1:
        obj = {}
        for _ in range(fdp.ConsumeIntInRange(0, 5)):
            key = fdp.ConsumeUnicodeNoSurrogates(16)
            obj[key] = _rand_scalar(fdp)
        return obj
    return _rand_scalar(fdp)


def TestOneInput(data: bytes) -> None:
    fdp = FuzzedDataProvider(data)

    raw_bytes = fdp.ConsumeBytes(256)
    raw_str = raw_bytes.decode("utf-8", errors="ignore")

    try:
        ujson.loads(raw_str)
    except (ValueError, TypeError):
        pass

    try:
        ujson.loads(raw_bytes)
    except (ValueError, TypeError):
        pass

    obj = _rand_object(fdp)
    try:
        dumped = ujson.dumps(obj)
        ujson.loads(dumped)
    except (ValueError, TypeError, OverflowError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
