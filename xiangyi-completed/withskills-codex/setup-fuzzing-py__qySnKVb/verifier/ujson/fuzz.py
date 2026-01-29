import sys

import atheris

with atheris.instrument_imports():
    import ujson


def _build_simple(fdp: atheris.FuzzedDataProvider):
    size = fdp.ConsumeIntInRange(0, 16)
    return [fdp.ConsumeIntInRange(-1000, 1000) for _ in range(size)]


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(400)

    try:
        obj = ujson.loads(text)
    except ValueError:
        obj = None

    if obj is not None:
        try:
            _ = ujson.dumps(obj)
        except OverflowError:
            return

    simple = _build_simple(fdp)
    try:
        dumped = ujson.dumps(simple)
        _ = ujson.loads(dumped)
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
