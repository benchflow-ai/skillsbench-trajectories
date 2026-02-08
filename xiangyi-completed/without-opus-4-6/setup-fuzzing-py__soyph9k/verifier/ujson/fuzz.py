"""Coverage-guided fuzz driver for the UltraJSON (ujson) library."""

import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for ujson encoding and decoding functions."""
    import ujson

    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz ujson.loads() with a string
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
            ujson.loads(text)

        elif choice == 1:
            # Fuzz ujson.loads() with bytes
            raw = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
            ujson.loads(raw)

        elif choice == 2:
            # Fuzz ujson.dumps() with constructed objects
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
            num_int = fdp.ConsumeIntInRange(-2**53, 2**53)
            num_float = fdp.ConsumeFloat()
            obj = {
                "str": text,
                "int": num_int,
                "float": num_float,
                "bool": fdp.ConsumeBool(),
                "null": None,
                "list": [text, num_int, num_float, None, True, False],
                "nested": {"a": text, "b": num_int},
            }
            result = ujson.dumps(obj)
            # Round-trip: verify loads(dumps(x)) doesn't crash
            ujson.loads(result)

        elif choice == 3:
            # Fuzz ujson.dumps() with various options
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
            ujson.dumps(
                text,
                ensure_ascii=fdp.ConsumeBool(),
                encode_html_chars=fdp.ConsumeBool(),
                escape_forward_slashes=fdp.ConsumeBool(),
                sort_keys=fdp.ConsumeBool(),
                indent=fdp.ConsumeIntInRange(0, 8),
            )

    except (
        ValueError,
        TypeError,
        OverflowError,
        ujson.JSONDecodeError,
        RecursionError,
        MemoryError,
    ):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
