#!/usr/bin/env python3
"""
Fuzzing driver for UltraJSON library using Atheris (LibFuzzer for Python)
Targets: JSON parsing (loads) and encoding (dumps) - focus on security vulnerabilities
"""

import sys
import atheris

# Suppress warnings for cleaner fuzzing output
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    """Fuzz target for UltraJSON library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz ujson.loads() - most critical for security
            json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10000))
            ujson.loads(json_string)

        elif choice == 1:
            # Fuzz ujson.loads() with bytes
            json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 10000))
            ujson.loads(json_bytes)

        elif choice == 2:
            # Fuzz ujson.dumps() with various Python objects
            obj_type = fdp.ConsumeIntInRange(0, 6)

            if obj_type == 0:
                # Dictionary
                obj = {}
                num_items = fdp.ConsumeIntInRange(0, 50)
                for _ in range(num_items):
                    key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
                    value = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
                    obj[key] = value

            elif obj_type == 1:
                # List
                obj = []
                num_items = fdp.ConsumeIntInRange(0, 100)
                for _ in range(num_items):
                    obj.append(fdp.ConsumeInt(8))

            elif obj_type == 2:
                # Numbers
                obj = fdp.ConsumeFloat()

            elif obj_type == 3:
                # Strings with special characters
                obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))

            elif obj_type == 4:
                # Boolean and None
                obj = fdp.PickValueInList([True, False, None])

            else:
                # Nested structure
                obj = {
                    "a": [1, 2, 3],
                    "b": {"nested": fdp.ConsumeUnicodeNoSurrogates(50)},
                    "c": fdp.ConsumeFloat()
                }

            ujson.dumps(obj)

        elif choice == 3:
            # Fuzz ujson.dumps() with encoding options
            obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            ensure_ascii = fdp.ConsumeBool()
            encode_html_chars = fdp.ConsumeBool()
            ujson.dumps(obj, ensure_ascii=ensure_ascii, encode_html_chars=encode_html_chars)

        elif choice == 4:
            # Fuzz with deeply nested structures
            depth = fdp.ConsumeIntInRange(1, 100)
            obj = fdp.ConsumeInt(4)
            for _ in range(depth):
                if fdp.ConsumeBool():
                    obj = [obj]
                else:
                    obj = {"key": obj}
            ujson.dumps(obj)
            ujson.loads(ujson.dumps(obj))

    except (ValueError, TypeError):
        # Expected exceptions - invalid JSON or types
        pass
    except (OverflowError, ):
        # Expected for very large numbers
        pass
    except (UnicodeDecodeError, UnicodeError):
        # Expected encoding errors
        pass
    except (RecursionError, ):
        # Expected for deeply nested structures
        pass
    except Exception as e:
        # Unexpected exceptions might indicate bugs
        error_type = type(e).__name__
        # These might indicate actual bugs in ujson
        if error_type not in ['MemoryError', 'KeyboardInterrupt', 'SystemExit']:
            # Log the error for investigation
            raise


def main():
    """Main fuzzing entry point."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
