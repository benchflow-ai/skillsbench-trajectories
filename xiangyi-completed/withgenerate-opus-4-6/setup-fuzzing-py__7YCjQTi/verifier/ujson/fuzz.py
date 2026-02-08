import sys
import atheris


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz ujson.loads with string input
            s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if s:
                ujson.loads(s)
        elif choice == 1:
            # Fuzz ujson.loads with bytes input
            b = fdp.ConsumeBytes(fdp.remaining_bytes())
            if b:
                ujson.loads(b)
        elif choice == 2:
            # Round-trip: decode then re-encode
            s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if s:
                obj = ujson.loads(s)
                encoded = ujson.dumps(obj)
                ujson.loads(encoded)
    except (
        ujson.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
        MemoryError,
        RecursionError,
        KeyError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        RuntimeError,
    ):
        pass


def main():
    atheris.instrument_all()
    global ujson
    import ujson as _ujson
    ujson = _ujson
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
