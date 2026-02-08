import sys
import atheris


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    import ujson

    # Fuzz ujson.loads() with bytes input - primary target
    try:
        ujson.loads(data)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass

    # Fuzz ujson.loads() with string input
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        ujson.loads(s)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass

    # Fuzz round-trip: encode then decode
    try:
        # Create a simple object from fuzz data
        choice = fdp.ConsumeIntInRange(0, 4)
        if choice == 0:
            obj = fdp.ConsumeFloat()
        elif choice == 1:
            obj = fdp.ConsumeInt(8)
        elif choice == 2:
            obj = fdp.ConsumeUnicodeNoSurrogates(64)
        elif choice == 3:
            obj = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))]
        else:
            obj = {fdp.ConsumeUnicodeNoSurrogates(8): fdp.ConsumeInt(4)}
        encoded = ujson.dumps(obj)
        ujson.loads(encoded)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
