"""Coverage-guided fuzz driver for the ujson library."""
import sys
import atheris

with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz ujson.loads with string input
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        try:
            ujson.loads(text)
        except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError,
                RecursionError, MemoryError, UnicodeDecodeError):
            pass

    elif choice == 1:
        # Fuzz ujson.loads with bytes input
        raw = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
        try:
            ujson.loads(raw)
        except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError,
                RecursionError, MemoryError, UnicodeDecodeError):
            pass

    elif choice == 2:
        # Fuzz ujson.dumps with various parameters
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        try:
            obj = ujson.loads(text)
        except Exception:
            # If we can't parse, create a simple fuzzed object
            obj = text

        ensure_ascii = fdp.ConsumeBool()
        sort_keys = fdp.ConsumeBool()
        encode_html = fdp.ConsumeBool()
        escape_slashes = fdp.ConsumeBool()
        indent = fdp.ConsumeIntInRange(0, 16)

        try:
            ujson.dumps(
                obj,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                encode_html_chars=encode_html,
                escape_forward_slashes=escape_slashes,
                indent=indent,
            )
        except (ValueError, TypeError, OverflowError, RecursionError,
                MemoryError, UnicodeDecodeError):
            pass

    else:
        # Round-trip fuzzing: decode then encode then decode
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        try:
            obj = ujson.loads(text)
            encoded = ujson.dumps(obj)
            obj2 = ujson.loads(encoded)
        except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError,
                RecursionError, MemoryError, UnicodeDecodeError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
