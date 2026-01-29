import sys
import atheris

with atheris.instrument_imports():
    import ujson


def _make_object(fdp: atheris.FuzzedDataProvider) -> object:
    return {
        "s": fdp.ConsumeUnicodeNoSurrogates(32),
        "n": fdp.ConsumeIntInRange(-1000000, 1000000),
        "b": fdp.ConsumeBool(),
        "arr": [fdp.ConsumeIntInRange(-1000, 1000) for _ in range(fdp.ConsumeIntInRange(0, 8))],
    }


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        choice = fdp.ConsumeIntInRange(0, 2)
        if choice == 0:
            text = fdp.ConsumeUnicodeNoSurrogates(256)
            ujson.loads(text)
        elif choice == 1:
            raw = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                return
            ujson.loads(text)
        else:
            obj = _make_object(fdp)
            ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
