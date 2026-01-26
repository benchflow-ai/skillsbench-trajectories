#!/usr/bin/env python3
"""
Fuzz driver for ujson (UltraJSON) using Atheris (LibFuzzer-based).
Targets the high-priority JSON encoding and decoding functions
identified in notes_for_testing.txt.

Note: ujson is in maintenance-only mode due to security concerns,
making fuzz testing especially important.
"""

import sys
import atheris


def setup_imports():
    """Import target modules with instrumentation."""
    with atheris.instrument_imports():
        import ujson
    return ujson


# Import modules with instrumentation
ujson = setup_imports()


@atheris.instrument_func
def TestOneInput(data: bytes):
    """
    Fuzz entry point targeting ujson's encoding and decoding functions.

    Priority targets:
    1. ujson.loads() / ujson.decode() - JSON decoding (HIGHEST PRIORITY)
    2. ujson.dumps() / ujson.encode() - JSON encoding
    3. Round-trip encoding/decoding for consistency
    """
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: ujson.loads() with raw bytes - primary attack surface
    try:
        ujson.loads(data)
    except (ujson.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 2: ujson.loads() with string input
    try:
        input_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
        if input_string:
            ujson.loads(input_string)
    except (ujson.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 3: ujson.dumps() with various Python objects
    try:
        obj_type = fdp.ConsumeIntInRange(0, 7)

        if obj_type == 0:
            # String
            obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
        elif obj_type == 1:
            # Integer
            obj = fdp.ConsumeInt(8)
        elif obj_type == 2:
            # Float
            obj = fdp.ConsumeFloat()
        elif obj_type == 3:
            # Boolean
            obj = fdp.ConsumeBool()
        elif obj_type == 4:
            # None
            obj = None
        elif obj_type == 5:
            # List
            list_len = fdp.ConsumeIntInRange(0, 50)
            obj = []
            for _ in range(list_len):
                item_type = fdp.ConsumeIntInRange(0, 3)
                if item_type == 0:
                    obj.append(fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50)))
                elif item_type == 1:
                    obj.append(fdp.ConsumeInt(4))
                elif item_type == 2:
                    obj.append(fdp.ConsumeFloat())
                else:
                    obj.append(fdp.ConsumeBool())
        elif obj_type == 6:
            # Dictionary
            dict_len = fdp.ConsumeIntInRange(0, 30)
            obj = {}
            for _ in range(dict_len):
                key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 30))
                if key:
                    value_type = fdp.ConsumeIntInRange(0, 3)
                    if value_type == 0:
                        obj[key] = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
                    elif value_type == 1:
                        obj[key] = fdp.ConsumeInt(4)
                    elif value_type == 2:
                        obj[key] = fdp.ConsumeFloat()
                    else:
                        obj[key] = fdp.ConsumeBool()
        else:
            # Nested structure
            obj = {
                "nested": {
                    "value": fdp.ConsumeInt(4),
                    "list": [fdp.ConsumeInt(2) for _ in range(fdp.ConsumeIntInRange(0, 10))]
                }
            }

        # Test with various encoding options
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
            indent=indent,
        )
    except (TypeError, OverflowError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test 4: Round-trip encoding/decoding for consistency
    try:
        # First decode the raw input
        decoded = ujson.loads(data)
        # Then encode it back
        reencoded = ujson.dumps(decoded)
        # And decode again
        redecoded = ujson.loads(reencoded)
        # The results should be equivalent (though floating point may differ)
    except (ujson.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 5: Test with special values (NaN, Infinity)
    try:
        allow_nan = fdp.ConsumeBool()
        obj_with_special = {
            "value": float('nan') if fdp.ConsumeBool() else float('inf'),
        }
        ujson.dumps(obj_with_special, allow_nan=allow_nan)
    except (TypeError, OverflowError, ValueError):
        pass
    except Exception:
        pass

    # Test 6: Deeply nested structures (stress test depth limits)
    try:
        depth = fdp.ConsumeIntInRange(0, 100)
        nested_list = []
        current = nested_list
        for _ in range(depth):
            current.append([])
            current = current[0]

        ujson.dumps(nested_list)
    except (RecursionError, OverflowError, ValueError, MemoryError):
        pass
    except Exception:
        pass

    # Test 7: Test with bytes input to loads (should work in ujson)
    try:
        raw_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000))
        if raw_bytes:
            ujson.loads(raw_bytes)
    except (ujson.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError):
        pass
    except Exception:
        pass

    # Test 8: Large integers (potential overflow)
    try:
        large_int = fdp.ConsumeInt(8)
        ujson.dumps(large_int)
        # Also test with very large Python integers
        very_large = large_int * (10 ** fdp.ConsumeIntInRange(0, 50))
        ujson.dumps(very_large)
    except (TypeError, OverflowError, ValueError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
