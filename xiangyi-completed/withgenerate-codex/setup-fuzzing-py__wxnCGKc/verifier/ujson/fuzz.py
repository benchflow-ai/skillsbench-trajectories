import sys

import atheris

with atheris.instrument_imports():
    import ujson


EXPECTED = (
    ValueError,
    TypeError,
    OverflowError,
)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(4096)
    try:
        obj = ujson.loads(text)
        ujson.dumps(obj)
    except EXPECTED:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
