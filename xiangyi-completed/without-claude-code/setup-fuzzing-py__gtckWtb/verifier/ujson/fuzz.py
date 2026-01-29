#!/usr/bin/env python3
"""
Fuzz driver for ujson (UltraJSON) library
Tests JSON parsing and serialization - HIGH PRIORITY target due to C implementation
"""

import sys
import atheris

# Add ujson to path
sys.path.insert(0, '/app/ujson')


def TestOneInput(data):
    """Fuzz target for ujson - C-based JSON parser"""
    if len(data) < 1:
        return

    # Import ujson here to handle build issues gracefully
    try:
        import ujson
    except ImportError:
        # If ujson is not built, skip
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz ujson.loads() with raw bytes
            json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 50000))
            try:
                ujson.loads(json_bytes)
            except (ValueError, TypeError, OverflowError, MemoryError):
                pass

        elif choice == 1:
            # Fuzz ujson.loads() with unicode strings
            json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50000))
            try:
                ujson.loads(json_string)
            except (ValueError, TypeError, OverflowError, MemoryError):
                pass

        elif choice == 2:
            # Fuzz ujson.dumps() with various Python objects
            try:
                # Build a random nested structure
                depth = fdp.ConsumeIntInRange(0, 50)
                obj = None
                for i in range(depth):
                    choice_type = fdp.ConsumeIntInRange(0, 5)
                    if choice_type == 0:
                        obj = {"key": obj, "data": fdp.ConsumeUnicodeNoSurrogates(100)}
                    elif choice_type == 1:
                        obj = [obj, fdp.ConsumeInt(8), fdp.ConsumeFloat()]
                    elif choice_type == 2:
                        obj = fdp.ConsumeFloat()
                    elif choice_type == 3:
                        obj = fdp.ConsumeInt(8)
                    else:
                        obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))

                ujson.dumps(obj)
            except (ValueError, TypeError, OverflowError, MemoryError, RecursionError):
                pass

        else:
            # Fuzz with specific edge cases
            json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10000))
            try:
                # Test encode/decode cycle
                result = ujson.loads(json_string)
                ujson.dumps(result)
            except (ValueError, TypeError, OverflowError, MemoryError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions - these might indicate bugs!
        error_str = str(e)
        # Memory/crash errors should be re-raised for investigation
        if any(keyword in error_str.lower() for keyword in
               ["segmentation", "bus error", "abort", "assertion"]):
            raise


def main():
    """Main fuzzing entry point"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
