"""Coverage-guided fuzz driver for the UltraJSON library.

Targets:
- ujson.loads() / ujson.decode() - JSON decoding from strings and bytes
- ujson.dumps() / ujson.encode() - JSON encoding (roundtrip testing)
"""
import sys
import atheris


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz decoding from string
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if not text:
                return
            obj = ujson.loads(text)
            # Roundtrip test
            encoded = ujson.dumps(obj)
            ujson.loads(encoded)
        elif choice == 1:
            # Fuzz decoding from bytes
            raw = fdp.ConsumeBytes(fdp.remaining_bytes())
            if not raw:
                return
            obj = ujson.loads(raw)
            encoded = ujson.dumps(obj)
            ujson.loads(encoded)
        else:
            # Fuzz with precise_float option
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if not text:
                return
            ujson.loads(text, precise_float=True)
    except (
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
        ujson.JSONDecodeError,
    ):
        pass


import ujson


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
