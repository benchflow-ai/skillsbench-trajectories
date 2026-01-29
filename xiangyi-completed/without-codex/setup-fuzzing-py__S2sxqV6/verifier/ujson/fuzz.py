import sys

import atheris

with atheris.instrument_imports():
    import ujson


def _make_obj(fdp, depth=0):
    if depth > 2:
        return fdp.ConsumeUnicodeNoSurrogates(32)

    choice = fdp.ConsumeIntInRange(0, 6)
    if choice == 0:
        return fdp.ConsumeIntInRange(-1_000_000_000, 1_000_000_000)
    if choice == 1:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 2:
        return fdp.ConsumeBytes(16)
    if choice == 3:
        return [
            _make_obj(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 5))
        ]
    if choice == 4:
        return {
            fdp.ConsumeUnicodeNoSurrogates(16): _make_obj(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 5))
        }
    if choice == 5:
        return fdp.ConsumeBool()
    return None


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    if fdp.ConsumeBool():
        payload = data if fdp.ConsumeBool() else fdp.ConsumeUnicodeNoSurrogates(1024)
        try:
            ujson.loads(payload)
        except (ValueError, TypeError, OverflowError):
            pass
    else:
        obj = _make_obj(fdp)
        try:
            ujson.dumps(
                obj,
                ensure_ascii=fdp.ConsumeBool(),
                encode_html_chars=fdp.ConsumeBool(),
                escape_forward_slashes=fdp.ConsumeBool(),
                indent=fdp.ConsumeIntInRange(0, 4),
            )
        except (TypeError, OverflowError, ValueError):
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
