#!/usr/bin/env python3
"""
Fuzz driver for UltraJSON (ujson)
Tests JSON encoding and decoding - HIGH VALUE TARGET (C extension)
"""

import atheris
import sys

# Suppress warnings during fuzzing
import warnings
warnings.filterwarnings("ignore")


def TestOneInput(data):
    """Fuzz target for ujson JSON parsing and encoding"""
    fdp = atheris.FuzzedDataProvider(data)

    # Import inside to catch import-time errors
    try:
        import ujson
    except Exception:
        return

    # Test different functions based on fuzzer choice
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Test ujson.loads() with random JSON strings
            json_str = fdp.ConsumeUnicodeNoSurrogates(1000)
            try:
                ujson.loads(json_str)
            except (ValueError, TypeError, OverflowError, RecursionError):
                pass

        elif choice == 1:
            # Test ujson.dumps() with various Python objects
            # Build a random Python object
            obj_type = fdp.ConsumeIntInRange(0, 6)

            if obj_type == 0:
                # Dict
                obj = {}
                for _ in range(fdp.ConsumeIntInRange(0, 20)):
                    key = fdp.ConsumeUnicodeNoSurrogates(50)
                    value = fdp.ConsumeUnicodeNoSurrogates(50)
                    obj[key] = value
            elif obj_type == 1:
                # List
                obj = [fdp.ConsumeUnicodeNoSurrogates(50)
                       for _ in range(fdp.ConsumeIntInRange(0, 20))]
            elif obj_type == 2:
                # Number
                obj = fdp.ConsumeFloat()
            elif obj_type == 3:
                # String
                obj = fdp.ConsumeUnicodeNoSurrogates(500)
            elif obj_type == 4:
                # Nested structure
                obj = {
                    "a": [1, 2, 3],
                    "b": {"nested": fdp.ConsumeUnicodeNoSurrogates(100)},
                    "c": fdp.ConsumeInt(8)
                }
            elif obj_type == 5:
                # Boolean/None
                obj = fdp.PickValueInList([True, False, None])
            else:
                # Very large number
                obj = fdp.ConsumeInt(8)

            try:
                ujson.dumps(obj)
            except (ValueError, TypeError, OverflowError, RecursionError):
                pass

        elif choice == 2:
            # Test ujson.dumps() with various options
            obj = {
                "key": fdp.ConsumeUnicodeNoSurrogates(100),
                "num": fdp.ConsumeInt(4),
                "float": fdp.ConsumeFloat()
            }

            try:
                ensure_ascii = fdp.ConsumeBool()
                encode_html_chars = fdp.ConsumeBool()
                escape_forward_slashes = fdp.ConsumeBool()
                sort_keys = fdp.ConsumeBool()
                indent = fdp.ConsumeIntInRange(0, 10)

                ujson.dumps(
                    obj,
                    ensure_ascii=ensure_ascii,
                    encode_html_chars=encode_html_chars,
                    escape_forward_slashes=escape_forward_slashes,
                    sort_keys=sort_keys,
                    indent=indent
                )
            except (ValueError, TypeError, OverflowError):
                pass

        else:
            # Test round-trip: dumps then loads
            # Build nested structure
            depth = fdp.ConsumeIntInRange(0, 10)
            obj = {"value": fdp.ConsumeUnicodeNoSurrogates(50)}
            for _ in range(depth):
                obj = {"nested": obj, "data": fdp.ConsumeInt(4)}

            try:
                json_str = ujson.dumps(obj)
                ujson.loads(json_str)
            except (ValueError, TypeError, OverflowError, RecursionError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions
        # For C extensions, we want to catch segfaults and crashes
        # but these will be caught by atheris
        error_str = str(e).lower()
        if 'assert' in error_str or 'unreachable' in error_str:
            raise
        # Otherwise suppress to continue fuzzing


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
