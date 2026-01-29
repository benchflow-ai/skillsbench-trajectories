#!/usr/bin/env python3
"""Fuzz driver for ujson library - JSON encoding/decoding."""

import sys
import atheris

with atheris.instrument_imports():
    import ujson


def TestOneInput(data: bytes) -> None:
    """Main fuzz target function for ujson library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Decode arbitrary JSON strings
    try:
        json_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 1000)
        )
        ujson.loads(json_str)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Test 2: Decode bytes directly
    try:
        json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 500))
        ujson.loads(json_bytes)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Test 3: Encode and decode round-trip with strings
    try:
        test_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 200)
        )
        encoded = ujson.dumps(test_str)
        ujson.loads(encoded)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Test 4: Encode with different options
    try:
        test_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 200)
        )
        ujson.dumps(
            test_str,
            encode_html_chars=fdp.ConsumeBool(),
            ensure_ascii=fdp.ConsumeBool(),
            escape_forward_slashes=fdp.ConsumeBool(),
        )
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Test 5: Encode with indent
    try:
        test_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 100)
        )
        indent = fdp.ConsumeIntInRange(0, 20)
        ujson.dumps(test_str, indent=indent)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
        pass

    # Test 6: Encode nested structures
    try:
        # Create a nested dict/list structure
        depth = fdp.ConsumeIntInRange(1, 10)
        obj = {}
        current = obj
        for i in range(depth):
            key = fdp.ConsumeUnicodeNoSurrogates(
                fdp.ConsumeIntInRange(1, 20)
            ) or f"key{i}"
            if fdp.ConsumeBool():
                current[key] = {}
                current = current[key]
            else:
                current[key] = []
                if current[key] is not None:
                    current[key].append({})
                    current = current[key][-1]

        ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeDecodeError):
        pass

    # Test 7: Encode numbers
    try:
        if fdp.ConsumeBool():
            num = fdp.ConsumeFloat()
        else:
            num = fdp.ConsumeInt(8)
        ujson.dumps(num)
    except (ValueError, TypeError, OverflowError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
