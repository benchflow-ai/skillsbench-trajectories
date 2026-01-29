import sys

import atheris

with atheris.instrument_imports():
    import ujson


def _build_obj(fdp: atheris.FuzzedDataProvider, depth: int = 0):
    if depth > 2:
        return fdp.ConsumeUnicodeNoSurrogates(20)
    choice = fdp.ConsumeIntInRange(0, 5)
    if choice == 0:
        return fdp.ConsumeIntInRange(-1000000, 1000000)
    if choice == 1:
        return fdp.ConsumeFloat()
    if choice == 2:
        return fdp.ConsumeUnicodeNoSurrogates(50)
    if choice == 3:
        return [
            _build_obj(fdp, depth + 1) for _ in range(fdp.ConsumeIntInRange(0, 3))
        ]
    if choice == 4:
        return {
            fdp.ConsumeUnicodeNoSurrogates(10): _build_obj(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        }
    return None if fdp.ConsumeBool() else fdp.ConsumeBool()


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        if fdp.ConsumeBool():
            blob = fdp.ConsumeBytes(200)
            try:
                ujson.loads(blob)
            except Exception:
                pass
        else:
            text = fdp.ConsumeUnicodeNoSurrogates(200)
            try:
                ujson.loads(text)
            except Exception:
                pass

        obj = _build_obj(fdp)
        try:
            dumped = ujson.dumps(obj)
            try:
                ujson.loads(dumped)
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
