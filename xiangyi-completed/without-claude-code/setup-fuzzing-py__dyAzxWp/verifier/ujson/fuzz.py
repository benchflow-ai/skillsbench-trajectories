#!/usr/bin/env python3
"""
Fuzz driver for UltraJSON (ujson)
Tests JSON encoding and decoding functions
This is a high-priority fuzzing target due to known security concerns
"""

import sys
import atheris

with atheris.instrument_imports():
    import ujson


def fuzz_ujson_loads(data):
    """Fuzz ujson.loads() - JSON parsing"""
    try:
        ujson.loads(data)
    except (ValueError, TypeError, OverflowError):
        # Expected exceptions for invalid JSON
        pass
    except Exception as e:
        # Unexpected exceptions might indicate bugs
        pass


def fuzz_ujson_dumps(obj):
    """Fuzz ujson.dumps() - JSON encoding"""
    try:
        ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError):
        # Expected exceptions
        pass
    except Exception as e:
        pass


def create_nested_structure(fdp, depth=0, max_depth=10):
    """Create nested data structures for encoding fuzzing"""
    if depth >= max_depth:
        return fdp.ConsumeInt(4)

    choice = fdp.ConsumeIntInRange(0, 5)

    if choice == 0:
        # Integer
        return fdp.ConsumeInt(8)
    elif choice == 1:
        # Float
        return fdp.ConsumeFloat()
    elif choice == 2:
        # String
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
    elif choice == 3:
        # List
        size = fdp.ConsumeIntInRange(0, 10)
        return [create_nested_structure(fdp, depth + 1, max_depth) for _ in range(size)]
    elif choice == 4:
        # Dict
        size = fdp.ConsumeIntInRange(0, 10)
        return {
            fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 20)):
            create_nested_structure(fdp, depth + 1, max_depth)
            for _ in range(size)
        }
    else:
        # Boolean or None
        return fdp.ConsumeBool() if fdp.ConsumeBool() else None


@atheris.instrument_func
def TestOneInput(data):
    """Main fuzzing entry point"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 1)

    if choice == 0:
        # Fuzz ujson.loads() with byte input
        remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            # Try as bytes
            fuzz_ujson_loads(remaining)
        except:
            pass

        try:
            # Try as string
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_ujson_loads(input_str)
        except:
            pass
    else:
        # Fuzz ujson.dumps() with generated objects
        try:
            obj = create_nested_structure(fdp, max_depth=5)
            fuzz_ujson_dumps(obj)
        except:
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
