import sys

import atheris
import ujson


MAX_DEPTH = 2


def _make_value(fdp: atheris.FuzzedDataProvider, depth: int = 0):
    kind = fdp.ConsumeIntInRange(0, 6 if depth < MAX_DEPTH else 4)
    if kind == 0:
        return None
    if kind == 1:
        return fdp.ConsumeBool()
    if kind == 2:
        return fdp.ConsumeInt(64)
    if kind == 3:
        return fdp.ConsumeFloat()
    if kind == 4:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if kind == 5:
        return [_make_value(fdp, depth + 1) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    return {
        fdp.ConsumeUnicodeNoSurrogates(32): _make_value(fdp, depth + 1)
        for _ in range(fdp.ConsumeIntInRange(0, 4))
    }


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(256)
    if text:
        try:
            obj = ujson.loads(text)
            ujson.dumps(obj)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass

    obj = _make_value(fdp)
    try:
        dumped = ujson.dumps(
            obj,
            ensure_ascii=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
            reject_bytes=fdp.ConsumeBool(),
            precise_float=fdp.ConsumeBool(),
            allow_nan=fdp.ConsumeBool(),
        )
        ujson.loads(dumped)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
