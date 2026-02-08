"""Coverage-guided fuzz driver for the ujson (UltraJSON) library."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for ujson's JSON parsing and encoding."""
    import ujson

    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz ujson.loads() with string input
        json_str = fdp.ConsumeUnicode(fdp.remaining_bytes())
        if not json_str:
            return
        try:
            ujson.loads(json_str)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                RecursionError, MemoryError):
            pass

    elif choice == 1:
        # Fuzz ujson.loads() with bytes input
        json_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())
        if not json_bytes:
            return
        try:
            ujson.loads(json_bytes)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                RecursionError, MemoryError, UnicodeDecodeError):
            pass

    elif choice == 2:
        # Fuzz ujson.dumps() with parsed objects, then roundtrip
        json_str = fdp.ConsumeUnicode(fdp.remaining_bytes())
        if not json_str:
            return
        try:
            obj = ujson.loads(json_str)
            encoded = ujson.dumps(obj)
            ujson.loads(encoded)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                RecursionError, MemoryError, TypeError):
            pass

    elif choice == 3:
        # Fuzz ujson.dumps() with various encoding options
        json_str = fdp.ConsumeUnicode(fdp.remaining_bytes())
        if not json_str:
            return
        try:
            obj = ujson.loads(json_str)
            # Test with different options
            ujson.dumps(obj, ensure_ascii=fdp.ConsumeBool() if fdp.remaining_bytes() > 0 else True)
            ujson.dumps(obj, sort_keys=True)
            ujson.dumps(obj, indent=2)
            ujson.dumps(obj, encode_html_chars=True)
            ujson.dumps(obj, escape_forward_slashes=False)
        except (ujson.JSONDecodeError, ValueError, OverflowError,
                RecursionError, MemoryError, TypeError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
