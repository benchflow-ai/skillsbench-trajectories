import sys

import atheris
import ujson


def _consume_text(fdp, max_len: int) -> str:
    return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, max_len))


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = _consume_text(fdp, 2048)

    # Try parsing as JSON
    try:
        obj = ujson.loads(text)
    except (ValueError, TypeError, OverflowError):
        obj = None

    # Try serializing back
    try:
        if obj is None:
            obj = {"text": text, "n": fdp.ConsumeIntInRange(-1_000_000, 1_000_000)}
        dumped = ujson.dumps(obj)
        ujson.loads(dumped)
    except (ValueError, TypeError, OverflowError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
