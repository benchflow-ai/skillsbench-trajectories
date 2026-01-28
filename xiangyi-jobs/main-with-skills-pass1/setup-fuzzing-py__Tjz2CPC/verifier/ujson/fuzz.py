import atheris
import sys

with atheris.instrument_imports():
    import ujson


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(400)
    try:
        if fdp.ConsumeBool():
            ujson.loads(text)
        else:
            ujson.loads(text.encode("utf-8", errors="ignore"))
        if fdp.ConsumeBool():
            obj = {
                "text": text,
                "num": fdp.ConsumeIntInRange(-1_000_000, 1_000_000),
                "flag": fdp.ConsumeBool(),
                "list": [fdp.ConsumeIntInRange(-10, 10) for _ in range(fdp.ConsumeIntInRange(0, 8))],
            }
            dumped = ujson.dumps(obj)
            ujson.loads(dumped)
    except (ValueError, TypeError, OverflowError):
        return


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
