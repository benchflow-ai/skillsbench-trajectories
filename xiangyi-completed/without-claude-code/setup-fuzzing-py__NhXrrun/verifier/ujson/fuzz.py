#!/usr/bin/env python3
"""
Coverage-guided fuzzer for ujson library using Atheris (LibFuzzer).
Targets JSON parsing and encoding functions.
"""

import sys
import atheris
import struct

# Enable coverage instrumentation before importing target modules
with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    """Fuzz target for ujson library."""

    # Need at least some bytes to work with
    if len(data) < 1:
        return

    # Test 1: ujson.decode() / ujson.loads() with bytes
    try:
        ujson.loads(data)
    except (
        ujson.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
        MemoryError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 2: ujson.decode() with string
    try:
        input_str = data.decode("utf-8", errors="ignore")
        if input_str:
            ujson.loads(input_str)
    except (
        ujson.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
        MemoryError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 3: ujson.encode() / ujson.dumps() with decoded object
    try:
        input_str = data.decode("utf-8", errors="ignore")
        if input_str:
            obj = ujson.loads(input_str)
            # Re-encode with various options
            ujson.dumps(obj)
            ujson.dumps(obj, ensure_ascii=True)
            ujson.dumps(obj, ensure_ascii=False)
            ujson.dumps(obj, encode_html_chars=True)
            ujson.dumps(obj, escape_forward_slashes=False)
            ujson.dumps(obj, sort_keys=True)
            ujson.dumps(obj, indent=2)
    except (
        ujson.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
        MemoryError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 4: encode Python objects constructed from input
    try:
        input_str = data.decode("utf-8", errors="ignore")
        # Create various Python objects with input data
        test_objects = [
            input_str,
            {"key": input_str},
            [input_str, 1, 2.5, None, True, False],
            {"nested": {"data": input_str}},
        ]
        for obj in test_objects:
            ujson.dumps(obj)
            ujson.dumps(obj, ensure_ascii=True)
            ujson.dumps(obj, ensure_ascii=False)
    except (
        ujson.JSONDecodeError,
        ValueError,
        TypeError,
        OverflowError,
        MemoryError,
        RecursionError,
    ):
        pass
    except Exception:
        pass

    # Test 5: Test with large indent values
    try:
        if len(data) >= 4:
            indent = struct.unpack('I', data[:4])[0] % 100  # Limit indent
            ujson.dumps({"test": "data"}, indent=indent)
    except (
        ValueError,
        TypeError,
        OverflowError,
        struct.error,
    ):
        pass
    except Exception:
        pass


def main():
    # Run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
