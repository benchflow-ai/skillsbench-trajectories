#!/usr/bin/env python3
"""
LibFuzzer-style fuzz driver for ujson library using Atheris.
Tests JSON encoding and decoding functions.
"""

import sys
import atheris

with atheris.instrument_imports():
    import ujson
    from decimal import Decimal
    from datetime import datetime


def TestOneInput(data):
    """Fuzz target for ujson library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Skip empty inputs
    if len(data) < 1:
        return

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz ujson.loads with string input
            json_string = fdp.ConsumeUnicodeNoSurrogates(500)
            if json_string:
                try:
                    ujson.loads(json_string)
                except (ValueError, ujson.JSONDecodeError, TypeError):
                    pass

        elif choice == 1:
            # Fuzz ujson.loads with bytes input
            json_bytes = fdp.ConsumeBytes(500)
            if json_bytes:
                try:
                    ujson.loads(json_bytes)
                except (ValueError, ujson.JSONDecodeError, TypeError, UnicodeDecodeError):
                    pass

        elif choice == 2:
            # Fuzz ujson.dumps with various Python objects
            obj_type = fdp.ConsumeIntInRange(0, 6)

            try:
                if obj_type == 0:
                    # Simple dict
                    obj = {
                        fdp.ConsumeString(20): fdp.ConsumeUnicodeNoSurrogates(50)
                        for _ in range(fdp.ConsumeIntInRange(0, 10))
                    }
                elif obj_type == 1:
                    # Nested structure
                    obj = {
                        'data': [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))],
                        'nested': {'key': fdp.ConsumeUnicodeNoSurrogates(30)}
                    }
                elif obj_type == 2:
                    # List with mixed types
                    obj = [
                        fdp.ConsumeInt(4),
                        fdp.ConsumeFloat(),
                        fdp.ConsumeUnicodeNoSurrogates(30),
                        fdp.ConsumeBool()
                    ]
                elif obj_type == 3:
                    # Large number (test overflow)
                    obj = fdp.ConsumeInt(8)
                elif obj_type == 4:
                    # Float (including special values)
                    obj = fdp.ConsumeFloat()
                elif obj_type == 5:
                    # String with special characters
                    obj = fdp.ConsumeUnicodeNoSurrogates(200)
                else:
                    # Boolean and None
                    obj = fdp.ConsumeBool() if fdp.ConsumeBool() else None

                # Try encoding with various options
                ensure_ascii = fdp.ConsumeBool()
                encode_html_chars = fdp.ConsumeBool()
                sort_keys = fdp.ConsumeBool()
                indent = fdp.ConsumeIntInRange(0, 8) if fdp.ConsumeBool() else 0

                ujson.dumps(
                    obj,
                    ensure_ascii=ensure_ascii,
                    encode_html_chars=encode_html_chars,
                    sort_keys=sort_keys,
                    indent=indent
                )
            except (ValueError, TypeError, OverflowError):
                pass

        elif choice == 3:
            # Fuzz round-trip encoding/decoding
            json_string = fdp.ConsumeUnicodeNoSurrogates(200)
            if json_string:
                try:
                    # Try to decode
                    obj = ujson.loads(json_string)
                    # Try to encode back
                    ujson.dumps(obj)
                except (ValueError, ujson.JSONDecodeError, TypeError, OverflowError):
                    pass

    except Exception as e:
        # Allow expected exceptions but catch unexpected crashes
        if not isinstance(e, (ValueError, TypeError, OverflowError,
                            ujson.JSONDecodeError, UnicodeDecodeError,
                            RecursionError)):
            raise


def main():
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
