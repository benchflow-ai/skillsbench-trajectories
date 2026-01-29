#!/usr/bin/env python3
"""
Atheris-based fuzzer for UltraJSON library
Targets: JSON parsing and encoding functions
PRIORITY: High security importance due to C implementation and maintenance-only status
"""

import sys
import atheris

# Suppress output for cleaner fuzzing
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    """Fuzz entry point called by Atheris"""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz ujson.loads() with arbitrary JSON strings
            json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 1000))
            ujson.loads(json_str)

        elif choice == 1:
            # Fuzz ujson.dumps() with various Python objects
            obj_type = fdp.ConsumeIntInRange(0, 6)
            if obj_type == 0:
                # Dictionary
                obj = {
                    fdp.ConsumeUnicodeNoSurrogates(10): fdp.ConsumeUnicodeNoSurrogates(20)
                    for _ in range(fdp.ConsumeIntInRange(0, 10))
                }
            elif obj_type == 1:
                # List
                obj = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 20))]
            elif obj_type == 2:
                # Nested structure
                obj = {
                    'nested': {
                        'list': [1, 2, 3],
                        'dict': {'key': 'value'}
                    }
                }
            elif obj_type == 3:
                # Numbers
                obj = fdp.PickValueInList([
                    fdp.ConsumeInt(8),
                    fdp.ConsumeFloat(),
                    float('inf'),
                    float('-inf'),
                    float('nan')
                ])
            elif obj_type == 4:
                # Strings with special characters
                obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            else:
                # Mixed types
                obj = {
                    'str': fdp.ConsumeUnicodeNoSurrogates(20),
                    'int': fdp.ConsumeInt(4),
                    'float': fdp.ConsumeFloat(),
                    'bool': fdp.ConsumeBool(),
                    'null': None,
                    'list': [1, 2, 3],
                    'dict': {'nested': 'value'}
                }

            # Fuzz with various encoding options
            ensure_ascii = fdp.ConsumeBool()
            encode_html_chars = fdp.ConsumeBool()
            escape_forward_slashes = fdp.ConsumeBool()
            sort_keys = fdp.ConsumeBool()
            indent = fdp.ConsumeIntInRange(0, 8) if fdp.ConsumeBool() else None

            ujson.dumps(
                obj,
                ensure_ascii=ensure_ascii,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                sort_keys=sort_keys,
                indent=indent
            )

        elif choice == 2:
            # Fuzz deeply nested structures
            depth = fdp.ConsumeIntInRange(1, 50)
            obj = {}
            current = obj
            for i in range(depth):
                current['nested'] = {}
                current = current['nested']
            ujson.dumps(obj)

        elif choice == 3:
            # Fuzz with malformed JSON strings
            json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 500))
            # Add random JSON-like characters
            chars = fdp.PickValueInList(['{', '}', '[', ']', '"', ':', ',', 'null', 'true', 'false'])
            json_str = chars + json_str + chars
            ujson.loads(json_str)

        elif choice == 4:
            # Fuzz round-trip encoding/decoding
            json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 300))
            try:
                decoded = ujson.loads(json_str)
                encoded = ujson.dumps(decoded)
                # Try to decode again
                ujson.loads(encoded)
            except:
                pass

    except (ValueError, TypeError, OverflowError, RecursionError,
            UnicodeDecodeError, MemoryError):
        # Expected exceptions during fuzzing
        pass
    except Exception as e:
        # Catch unexpected exceptions - these might indicate bugs
        error_msg = str(e).lower()
        if any(x in error_msg for x in ["maximum recursion", "out of memory"]):
            pass
        else:
            # Re-raise to find bugs - especially important for ujson
            # due to its C implementation and security history
            raise


def main():
    """Initialize and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
