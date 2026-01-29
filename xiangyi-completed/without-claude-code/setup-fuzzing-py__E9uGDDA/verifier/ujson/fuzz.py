#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for ujson library.
Tests ujson's encoding and decoding functions.
"""

import sys
import atheris
import ujson


def __test_one_input(data: bytes) -> None:
    """Fuzz driver for ujson library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Split fuzzed data into parts for different test strategies
    action = fdp.ConsumeIntInRange(0, 9)

    if action == 0:
        # Test ujson.decode() with fuzzed JSON string
        try:
            json_str = fdp.ConsumeUnicode(4096)
            ujson.decode(json_str)
        except (ujson.JSONDecodeError, ValueError, TypeError):
            pass

    elif action == 1:
        # Test ujson.decode() with fuzzed bytes
        try:
            json_bytes = fdp.ConsumeBytes(4096)
            ujson.decode(json_bytes)
        except (ujson.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError):
            pass

    elif action == 2:
        # Test ujson.encode() with basic Python types
        try:
            obj = fdp.ConsumeInt(2**31 - 1)
            ujson.encode(obj)
        except (TypeError, ValueError, OverflowError):
            pass

    elif action == 3:
        # Test ujson.encode() with string
        try:
            obj = fdp.ConsumeUnicode(4096)
            ujson.encode(obj)
        except (TypeError, ValueError):
            pass

    elif action == 4:
        # Test ujson.encode() with encoding options
        try:
            obj = fdp.ConsumeUnicode(1024)
            ensure_ascii = fdp.ConsumeBool()
            sort_keys = fdp.ConsumeBool()
            indent = fdp.ConsumeIntInRange(0, 16)
            ujson.encode(
                obj,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                indent=indent
            )
        except (TypeError, ValueError):
            pass

    elif action == 5:
        # Test ujson.encode() with list
        try:
            # Build a simple list from fuzzed data
            items = []
            for _ in range(fdp.ConsumeIntInRange(0, 20)):
                choice = fdp.ConsumeIntInRange(0, 3)
                if choice == 0:
                    items.append(fdp.ConsumeInt(1000))
                elif choice == 1:
                    items.append(fdp.ConsumeUnicode(100))
                else:
                    items.append(fdp.ConsumeBool())
            ujson.encode(items)
        except (TypeError, ValueError):
            pass

    elif action == 6:
        # Test ujson.encode() with dict
        try:
            obj = {}
            for _ in range(fdp.ConsumeIntInRange(0, 20)):
                key = fdp.ConsumeUnicode(64)
                choice = fdp.ConsumeIntInRange(0, 3)
                if choice == 0:
                    obj[key] = fdp.ConsumeInt(1000)
                elif choice == 1:
                    obj[key] = fdp.ConsumeUnicode(100)
                else:
                    obj[key] = fdp.ConsumeBool()

            sort_keys = fdp.ConsumeBool()
            ujson.encode(obj, sort_keys=sort_keys)
        except (TypeError, ValueError):
            pass

    elif action == 7:
        # Test ujson.encode() with special floats
        try:
            values = [
                float('inf'),
                float('-inf'),
                float('nan'),
                1.23e-10,
                1e308
            ]
            allow_nan = fdp.ConsumeBool()
            obj = values[fdp.ConsumeIntInRange(0, len(values) - 1)]
            ujson.encode(obj, allow_nan=allow_nan)
        except (TypeError, ValueError):
            pass

    elif action == 8:
        # Test encode/decode round-trip
        try:
            obj = fdp.ConsumeUnicode(1024)
            encoded = ujson.encode(obj)
            ujson.decode(encoded)
        except (TypeError, ValueError, ujson.JSONDecodeError):
            pass

    elif action == 9:
        # Test ujson.encode() with HTML escaping
        try:
            obj = fdp.ConsumeUnicode(512)
            encode_html = fdp.ConsumeBool()
            escape_slash = fdp.ConsumeBool()
            ujson.encode(
                obj,
                encode_html_chars=encode_html,
                escape_forward_slashes=escape_slash
            )
        except (TypeError, ValueError):
            pass


# Initialize atheris for code coverage guidance
atheris.Setup(sys.argv, __test_one_input)

if __name__ == "__main__":
    atheris.Fuzz()
