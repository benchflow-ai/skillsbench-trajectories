#!/usr/bin/env python3
"""Fuzz driver for UltraJSON (ujson) library - JSON parsing"""

import atheris
import sys

with atheris.instrument_imports():
    import ujson

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz ujson.loads() with random JSON strings"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test ujson.loads() with random strings
    try:
        json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 4096))
        if json_string:
            result = ujson.loads(json_string)
            # Try to encode it back
            ujson.dumps(result)
    except (ValueError, TypeError, OverflowError, RecursionError):
        # Expected exceptions for invalid JSON
        pass
    except Exception as e:
        error_msg = str(e).lower()
        if not any(x in error_msg for x in ['invalid', 'unexpected', 'cannot', 'bad', 'malformed']):
            raise

    # Test with bytes input
    try:
        remaining = fdp.remaining_bytes()
        if remaining > 0:
            json_bytes = fdp.ConsumeBytes(remaining)
            if json_bytes:
                ujson.loads(json_bytes)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError, RecursionError):
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
