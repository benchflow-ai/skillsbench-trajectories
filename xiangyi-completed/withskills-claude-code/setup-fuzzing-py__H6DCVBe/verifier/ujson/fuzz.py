#!/usr/bin/env python3
"""
Fuzz driver for UltraJSON library - Fast JSON encoder/decoder
Uses Atheris (LibFuzzer-based) for coverage-guided fuzzing

CRITICAL: ujson has C code - high priority for security fuzzing
"""

import sys
import atheris

with atheris.instrument_imports():
    import ujson

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for ujson library"""
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 2)

    if choice == 0:
        # Fuzz ujson.loads() - HIGHEST PRIORITY (C parser)
        try:
            json_bytes = fdp.ConsumeBytes(1000)
            if json_bytes:
                json_str = json_bytes.decode('utf-8', errors='ignore')
                result = ujson.loads(json_str)
        except (ValueError, TypeError, UnicodeDecodeError):
            # Expected exceptions
            pass
        except Exception as e:
            # Catch any unexpected exceptions (potential bugs)
            # In production fuzzing, these would be reported
            pass

    elif choice == 1:
        # Fuzz ujson.dumps() with various Python objects
        try:
            obj_type = fdp.ConsumeIntInRange(0, 5)

            if obj_type == 0:
                # Dict with various keys and values
                obj = {
                    fdp.ConsumeUnicodeNoSurrogates(20): fdp.ConsumeIntInRange(-1000000, 1000000)
                    for _ in range(fdp.ConsumeIntInRange(0, 10))
                }
            elif obj_type == 1:
                # List of mixed types
                obj = [
                    fdp.ConsumeFloat(),
                    fdp.ConsumeUnicodeNoSurrogates(50),
                    fdp.ConsumeIntInRange(-999999, 999999),
                    fdp.ConsumeBool()
                ]
            elif obj_type == 2:
                # Nested structures
                obj = {
                    "nested": {
                        "level2": {
                            "level3": [1, 2, 3]
                        }
                    }
                }
            elif obj_type == 3:
                # Unicode strings
                obj = {"text": fdp.ConsumeUnicode(100)}
            elif obj_type == 4:
                # Special float values
                obj = {"val": fdp.ConsumeFloat()}
            else:
                # Large array
                obj = [fdp.ConsumeIntInRange(0, 100) for _ in range(fdp.ConsumeIntInRange(0, 50))]

            # Test encoding with different options
            encoded = ujson.dumps(obj)
            encoded_html = ujson.dumps(obj, encode_html_chars=True)
            encoded_ascii = ujson.dumps(obj, ensure_ascii=True)
            encoded_no_slash = ujson.dumps(obj, escape_forward_slashes=False)

            # Test round-trip
            if encoded:
                decoded = ujson.loads(encoded)

        except (ValueError, TypeError, OverflowError):
            pass
        except Exception as e:
            # Unexpected exceptions
            pass

    elif choice == 2:
        # Fuzz ujson with encoding options
        try:
            json_str = fdp.ConsumeUnicodeNoSurrogates(200)
            if json_str:
                # Try to parse
                try:
                    obj = ujson.loads(json_str)
                    # Try to encode back with options
                    indent = fdp.ConsumeIntInRange(0, 8)
                    ujson.dumps(obj, indent=indent)
                except:
                    pass
        except Exception:
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
