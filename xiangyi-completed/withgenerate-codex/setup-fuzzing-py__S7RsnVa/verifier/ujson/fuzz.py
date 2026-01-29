import sys

import atheris
import ujson


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(512)

    try:
        obj = ujson.loads(text)
    except ValueError:
        return

    try:
        ujson.dumps(obj)
    except (TypeError, OverflowError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
