import sys

import atheris

with atheris.instrument_imports():
    import ujson


def _gen_value(fdp: atheris.FuzzedDataProvider, depth: int):
    if depth <= 0:
        choice = fdp.ConsumeIntInRange(0, 4)
    else:
        choice = fdp.ConsumeIntInRange(0, 6)

    if choice == 0:
        return None
    if choice == 1:
        return fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if choice == 2:
        return fdp.ConsumeFloat()
    if choice == 3:
        return fdp.ConsumeBool()
    if choice == 4:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 5:
        return [_gen_value(fdp, depth - 1) for _ in range(fdp.ConsumeIntInRange(0, 5))]
    return {
        fdp.ConsumeUnicodeNoSurrogates(16): _gen_value(fdp, depth - 1)
        for _ in range(fdp.ConsumeIntInRange(0, 5))
    }


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    text = fdp.ConsumeUnicodeNoSurrogates(512)
    try:
        ujson.loads(text)
    except (ValueError, TypeError, OverflowError):
        pass

    obj = _gen_value(fdp, 3)
    try:
        encoded = ujson.dumps(obj)
        ujson.loads(encoded)
    except (TypeError, ValueError, OverflowError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
