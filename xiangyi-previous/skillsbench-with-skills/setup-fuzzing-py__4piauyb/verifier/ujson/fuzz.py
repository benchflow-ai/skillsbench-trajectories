import sys
import atheris
import ujson


def gen_value(fdp: atheris.FuzzedDataProvider, depth: int = 0):
    if depth > 2:
        return fdp.ConsumeUnicodeNoSurrogates(20)
    choice = fdp.ConsumeIntInRange(0, 5)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(20)
    if choice == 1:
        return fdp.ConsumeIntInRange(-10**6, 10**6)
    if choice == 2:
        return fdp.ConsumeFloat()
    if choice == 3:
        return fdp.ConsumeBool()
    if choice == 4:
        return [gen_value(fdp, depth + 1) for _ in range(fdp.ConsumeIntInRange(0, 3))]
    # dict
    d = {}
    for _ in range(fdp.ConsumeIntInRange(0, 3)):
        k = fdp.ConsumeUnicodeNoSurrogates(10)
        d[k] = gen_value(fdp, depth + 1)
    return d


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(200)
    try:
        ujson.loads(s)
    except Exception:
        pass
    obj = gen_value(fdp)
    try:
        ujson.dumps(
            obj,
            ensure_ascii=fdp.ConsumeBool(),
            encode_html_chars=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
            indent=fdp.ConsumeIntInRange(0, 4),
        )
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
