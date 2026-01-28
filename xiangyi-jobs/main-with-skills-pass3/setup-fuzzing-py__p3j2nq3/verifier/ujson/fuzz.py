import sys
import atheris

with atheris.instrument_imports():
    import ujson


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _build_obj(fdp: atheris.FuzzedDataProvider, depth: int = 0):
    if depth > 3:
        return fdp.ConsumeIntInRange(-1000, 1000)
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
        return [
            _build_obj(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 4))
        ]
    return {
        fdp.ConsumeUnicodeNoSurrogates(10): _build_obj(fdp, depth + 1)
        for _ in range(fdp.ConsumeIntInRange(0, 4))
    }


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(500)

    _safe_call(ujson.loads, data)
    _safe_call(ujson.loads, text)

    obj = _build_obj(fdp)
    _safe_call(
        ujson.dumps,
        obj,
        ensure_ascii=fdp.ConsumeBool(),
        escape_forward_slashes=fdp.ConsumeBool(),
        sort_keys=fdp.ConsumeBool(),
    )


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
