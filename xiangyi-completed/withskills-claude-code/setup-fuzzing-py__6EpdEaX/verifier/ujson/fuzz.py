#!/usr/bin/env python3
"""UltraJSON library fuzzer using Atheris"""

import atheris
import sys

with atheris.instrument_imports():
    import ujson

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz UltraJSON's loads/decode function"""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Test with bytes input
        json_bytes = fdp.ConsumeBytes(len(data) // 2)
        try:
            result = ujson.loads(json_bytes)
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
            # Expected exceptions for malformed JSON
            pass

        # Test with string input
        json_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 5000))
        try:
            result = ujson.loads(json_string)
        except (ValueError, TypeError, OverflowError):
            # Expected exceptions for malformed JSON
            pass

        # Test with numeric values
        if len(data) > 10:
            numeric_str = str(fdp.ConsumeInt(8))
            try:
                result = ujson.loads(numeric_str)
            except (ValueError, TypeError):
                pass

            # Test with special float values
            special_floats = ["NaN", "Infinity", "-Infinity", "1e999999"]
            for special in special_floats:
                try:
                    result = ujson.loads(special)
                except (ValueError, TypeError, OverflowError):
                    pass

        # Test with array structures
        if len(data) > 20:
            array_str = "[" + fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 500)) + "]"
            try:
                result = ujson.loads(array_str)
            except (ValueError, TypeError, OverflowError):
                pass

        # Test with object structures
        if len(data) > 30:
            object_str = '{"' + fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100)) + '":' + \
                        fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100)) + '}'
            try:
                result = ujson.loads(object_str)
            except (ValueError, TypeError, OverflowError):
                pass

        # Test with unicode escape sequences
        if len(data) > 40:
            unicode_str = '"\\u0041\\u0042\\u0043"'
            try:
                result = ujson.loads(unicode_str)
            except (ValueError, TypeError, OverflowError):
                pass

    except Exception:
        # Catch any unexpected exceptions and report them
        raise

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
