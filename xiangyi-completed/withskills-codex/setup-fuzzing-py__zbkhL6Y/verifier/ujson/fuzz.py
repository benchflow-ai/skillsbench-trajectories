import sys
import atheris


def _load():
    with atheris.instrument_imports():
        import ujson
    return ujson


ujson = _load()


def _make_obj(fdp, depth=0):
    if depth > 2:
        return fdp.ConsumeInt(32)
    choice = fdp.ConsumeIntInRange(0, 5)
    if choice == 0:
        return fdp.ConsumeInt(64)
    if choice == 1:
        return fdp.ConsumeFloat()
    if choice == 2:
        return fdp.ConsumeUnicodeNoSurrogates(50)
    if choice == 3:
        return fdp.ConsumeBool()
    if choice == 4:
        return None
    if choice == 5:
        size = fdp.ConsumeIntInRange(0, 5)
        if fdp.ConsumeBool():
            return [_make_obj(fdp, depth + 1) for _ in range(size)]
        obj = {}
        for _ in range(size):
            key = fdp.ConsumeUnicodeNoSurrogates(20)
            obj[key] = _make_obj(fdp, depth + 1)
        return obj


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(400)
    ensure_ascii = fdp.ConsumeBool()
    encode_html_chars = fdp.ConsumeBool()
    escape_forward_slashes = fdp.ConsumeBool()
    indent = fdp.ConsumeIntInRange(0, 4)

    try:
        choice = fdp.ConsumeIntInRange(0, 2)
        if choice == 0:
            ujson.loads(text)
        elif choice == 1:
            obj = _make_obj(fdp)
            dumped = ujson.dumps(
                obj,
                ensure_ascii=ensure_ascii,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                indent=indent,
            )
            ujson.loads(dumped)
        else:
            ujson.dumps(text)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
