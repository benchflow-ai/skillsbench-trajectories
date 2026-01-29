import os
import sys

import atheris

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import ujson


def _build_value(fdp: atheris.FuzzedDataProvider, depth: int):
    if depth <= 0:
        choice = fdp.ConsumeIntInRange(0, 4)
    else:
        choice = fdp.ConsumeIntInRange(0, 6)

    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 1:
        return fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if choice == 2:
        return fdp.ConsumeFloat()
    if choice == 3:
        return fdp.ConsumeBool()
    if choice == 4:
        return None
    if choice == 5:
        size = fdp.ConsumeIntInRange(0, 5)
        return [_build_value(fdp, depth - 1) for _ in range(size)]
    size = fdp.ConsumeIntInRange(0, 5)
    return {fdp.ConsumeUnicodeNoSurrogates(16): _build_value(fdp, depth - 1) for _ in range(size)}


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    raw = fdp.ConsumeBytes(256)
    try:
        ujson.loads(raw)
    except Exception:
        pass

    try:
        text = fdp.ConsumeUnicodeNoSurrogates(256)
        ujson.loads(text)
    except Exception:
        pass

    try:
        obj = _build_value(fdp, 2)
        ujson.dumps(
            obj,
            ensure_ascii=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
            sort_keys=fdp.ConsumeBool(),
            allow_nan=fdp.ConsumeBool(),
            indent=fdp.ConsumeIntInRange(0, 4),
        )
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
