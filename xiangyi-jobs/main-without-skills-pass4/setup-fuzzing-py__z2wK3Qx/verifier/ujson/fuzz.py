import sys

import atheris

with atheris.instrument_imports():
    import ujson


def _make_basic_value(fdp: atheris.FuzzedDataProvider):
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.ConsumeIntInRange(-10**9, 10**9)
    if choice == 1:
        return fdp.ConsumeUnicodeNoSurrogates(100)
    if choice == 2:
        return fdp.ConsumeFloat()
    if choice == 3:
        return fdp.ConsumeBool()
    return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    json_bytes = fdp.ConsumeBytes(512)
    try:
        parsed = ujson.loads(json_bytes)
        if fdp.ConsumeBool():
            ujson.dumps(parsed)
    except Exception:
        pass

    try:
        value = [_make_basic_value(fdp) for _ in range(fdp.ConsumeIntInRange(0, 8))]
        ujson.dumps(
            value,
            ensure_ascii=fdp.ConsumeBool(),
            sort_keys=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
        )
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
