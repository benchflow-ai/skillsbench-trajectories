#!/usr/bin/env python3
"""
Fuzz driver for UltraJSON (ujson) - Fast JSON parser
Focuses on ujson.loads() which is the C parser - CRITICAL FOR SECURITY
"""
import sys
import atheris

# Import after atheris for better instrumentation
with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    """Fuzz ujson.loads() and ujson.dumps()"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Parse JSON string (PRIMARY FOCUS - C parser)
    json_str = fdp.ConsumeUnicodeNoSurrogates(1000)
    try:
        # This calls the C parser - most critical for finding bugs
        obj = ujson.loads(json_str)
    except (ValueError, TypeError, OverflowError):
        # Expected exceptions for invalid JSON
        pass

    # Test 2: Parse bytes
    if fdp.remaining_bytes() > 50:
        json_bytes = fdp.ConsumeBytes(500)
        try:
            obj = ujson.loads(json_bytes)
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
            pass

    # Test 3: Serialize various Python objects
    if fdp.remaining_bytes() > 20:
        # Create a random Python object and try to serialize it
        choice = fdp.ConsumeIntInRange(0, 6)
        try:
            if choice == 0:
                # String
                s = fdp.ConsumeUnicodeNoSurrogates(100)
                result = ujson.dumps(s)
            elif choice == 1:
                # Number
                n = fdp.ConsumeFloat()
                result = ujson.dumps(n)
            elif choice == 2:
                # List with mixed types
                lst = [
                    fdp.ConsumeInt(8),
                    fdp.ConsumeUnicodeNoSurrogates(50),
                    fdp.ConsumeBool()
                ]
                result = ujson.dumps(lst)
            elif choice == 3:
                # Dict
                d = {
                    fdp.ConsumeUnicodeNoSurrogates(20): fdp.ConsumeInt(4),
                    fdp.ConsumeUnicodeNoSurrogates(20): fdp.ConsumeUnicodeNoSurrogates(30)
                }
                result = ujson.dumps(d)
            elif choice == 4:
                # Nested structure
                nested = {
                    "a": [1, 2, {"b": fdp.ConsumeUnicodeNoSurrogates(30)}],
                    "c": fdp.ConsumeInt(8)
                }
                result = ujson.dumps(nested)
            elif choice == 5:
                # Very large number
                big_num = fdp.ConsumeInt(8)
                result = ujson.dumps(big_num)
            else:
                # Boolean and None
                result = ujson.dumps([True, False, None])

        except (ValueError, TypeError, OverflowError, MemoryError):
            # Expected exceptions for unserializable objects
            pass

    # Test 4: Edge case - very deep nesting (can cause stack overflow)
    if fdp.remaining_bytes() > 100:
        depth = fdp.ConsumeIntInRange(1, 100)
        nested_json = "[" * depth + "1" + "]" * depth
        try:
            obj = ujson.loads(nested_json)
        except (ValueError, TypeError, OverflowError, RecursionError, MemoryError):
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
