#!/usr/bin/env python3
"""Coverage-guided fuzzing for ujson library."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for ujson library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Import ujson inside to ensure instrumentation
    import ujson

    # Test 1: Decode JSON strings (primary target)
    try:
        json_str = fdp.ConsumeUnicodeNoSurrogates(5000)
        if json_str:
            ujson.loads(json_str)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except ujson.JSONDecodeError:
        pass

    # Test 2: Decode JSON bytes
    try:
        json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 5000))
        if json_bytes:
            ujson.loads(json_bytes)
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeDecodeError):
        pass
    except ujson.JSONDecodeError:
        pass

    # Test 3: Encode Python objects
    try:
        # Build a random Python structure
        choice = fdp.ConsumeIntInRange(0, 4)
        obj = None

        if choice == 0:
            # Dict
            obj = {
                fdp.ConsumeUnicodeNoSurrogates(20): fdp.ConsumeUnicodeNoSurrogates(100)
                for _ in range(fdp.ConsumeIntInRange(0, 10))
            }
        elif choice == 1:
            # List
            obj = [fdp.ConsumeUnicodeNoSurrogates(50) for _ in range(fdp.ConsumeIntInRange(0, 20))]
        elif choice == 2:
            # Nested structure
            obj = {
                "str": fdp.ConsumeUnicodeNoSurrogates(100),
                "int": fdp.ConsumeInt(8),
                "float": fdp.ConsumeFloat(),
                "bool": fdp.ConsumeBool(),
                "null": None,
                "list": [1, 2, 3],
            }
        elif choice == 3:
            # Large integer
            obj = fdp.ConsumeInt(16)
        else:
            # Float edge cases
            obj = fdp.ConsumeFloat()

        ujson.dumps(obj, ensure_ascii=fdp.ConsumeBool())
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass

    # Test 4: Encode with various options
    try:
        obj = {"key": fdp.ConsumeUnicodeNoSurrogates(200)}
        ujson.dumps(
            obj,
            ensure_ascii=fdp.ConsumeBool(),
            encode_html_chars=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
            sort_keys=fdp.ConsumeBool(),
            indent=fdp.ConsumeIntInRange(0, 10),
            allow_nan=fdp.ConsumeBool(),
        )
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass

    # Test 5: Roundtrip encode/decode
    try:
        obj = {
            "data": fdp.ConsumeUnicodeNoSurrogates(500),
            "number": fdp.ConsumeInt(4),
        }
        encoded = ujson.dumps(obj)
        decoded = ujson.loads(encoded)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except ujson.JSONDecodeError:
        pass

    # Test 6: Deeply nested structures
    try:
        depth = fdp.ConsumeIntInRange(0, 100)
        obj = "value"
        for _ in range(depth):
            if fdp.ConsumeBool():
                obj = [obj]
            else:
                obj = {"nested": obj}
        ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass


def main():
    # Instrument imports
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
