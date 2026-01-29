import sys
import atheris

with atheris.instrument_imports():
    import ujson


def _build_obj(fdp: atheris.FuzzedDataProvider, depth: int):
    if depth <= 0:
        choice = fdp.ConsumeIntInRange(0, 4)
    else:
        choice = fdp.ConsumeIntInRange(0, 6)

    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(50)
    if choice == 1:
        return fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    if choice == 2:
        return fdp.ConsumeFloat()
    if choice == 3:
        return fdp.ConsumeBool()
    if choice == 4:
        return None
    if choice == 5:
        length = fdp.ConsumeIntInRange(0, 5)
        return [_build_obj(fdp, depth - 1) for _ in range(length)]
    if choice == 6:
        length = fdp.ConsumeIntInRange(0, 5)
        obj = {}
        for _ in range(length):
            key = fdp.ConsumeUnicodeNoSurrogates(20)
            if not key:
                key = "k"
            obj[key] = _build_obj(fdp, depth - 1)
        return obj
    return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    try:
        ujson.loads(data)
    except Exception:
        pass

    text = fdp.ConsumeUnicodeNoSurrogates(200)
    if text:
        try:
            ujson.loads(text)
        except Exception:
            pass

    obj = _build_obj(fdp, depth=3)
    try:
        ujson.dumps(obj)
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
