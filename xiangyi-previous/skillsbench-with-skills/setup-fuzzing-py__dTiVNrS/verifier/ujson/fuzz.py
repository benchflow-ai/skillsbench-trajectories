import os
import sys

import atheris

sys.path.insert(0, os.path.dirname(__file__))

import ujson  # noqa: E402


def _build_value(fdp: atheris.FuzzedDataProvider, depth: int):
    if depth <= 0:
        choice = fdp.ConsumeIntInRange(0, 4)
        if choice == 0:
            return None
        if choice == 1:
            return fdp.ConsumeBool()
        if choice == 2:
            return fdp.ConsumeIntInRange(-1000000, 1000000)
        if choice == 3:
            return fdp.ConsumeFloat()
        return fdp.ConsumeUnicodeNoSurrogates(64)

    choice = fdp.ConsumeIntInRange(0, 2)
    if choice == 0:
        return [
            _build_value(fdp, depth - 1)
            for _ in range(fdp.ConsumeIntInRange(0, 4))
        ]
    if choice == 1:
        result = {}
        for _ in range(fdp.ConsumeIntInRange(0, 4)):
            key = fdp.ConsumeUnicodeNoSurrogates(16)
            result[key] = _build_value(fdp, depth - 1)
        return result
    return _build_value(fdp, depth - 1)


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(256)

    obj = None
    try:
        obj = ujson.loads(text)
    except Exception:
        obj = None

    if obj is not None:
        try:
            dumped = ujson.dumps(obj)
            _ = ujson.loads(dumped)
        except Exception:
            pass

    try:
        generated = _build_value(fdp, 2)
        dumped = ujson.dumps(generated)
        _ = ujson.loads(dumped)
    except Exception:
        pass

    try:
        decoder = getattr(ujson, "decode", None)
        if decoder is not None:
            _ = decoder(text)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
