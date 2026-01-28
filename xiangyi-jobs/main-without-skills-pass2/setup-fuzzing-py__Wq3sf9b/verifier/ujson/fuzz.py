import sys
import atheris
import ujson


def _consume_obj(fdp: atheris.FuzzedDataProvider, depth: int):
    if depth <= 0 or fdp.remaining_bytes() <= 0:
        choice = fdp.ConsumeIntInRange(0, 4)
    else:
        choice = fdp.ConsumeIntInRange(0, 6)

    if choice == 0:
        return fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if choice == 1:
        return fdp.ConsumeFloat()
    if choice == 2:
        return fdp.ConsumeBool()
    if choice == 3:
        return None
    if choice == 4:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 5:
        return [_consume_obj(fdp, depth - 1) for _ in range(fdp.ConsumeIntInRange(0, 6))]

    # dict
    size = fdp.ConsumeIntInRange(0, 6)
    result = {}
    for _ in range(size):
        key = fdp.ConsumeUnicodeNoSurrogates(16)
        result[key] = _consume_obj(fdp, depth - 1)
    return result


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    json_text = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        ujson.loads(json_text)
    except (ValueError, TypeError, OverflowError):
        pass

    obj = _consume_obj(fdp, depth=3)
    try:
        ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
