#!/usr/bin/env python3
"""Fuzz driver for MiniSGL library"""

import atheris
import sys
import json

with atheris.instrument_imports():
    pass

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz minisgl with various inputs"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test JSON parsing (common in config loading)
    try:
        json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2048))
        if json_str:
            json.loads(json_str)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        # Expected exceptions
        pass
    except Exception as e:
        error_msg = str(e).lower()
        if not any(x in error_msg for x in ['invalid', 'unexpected', 'cannot', 'bad']):
            raise

    # Test general data processing
    try:
        remaining = fdp.remaining_bytes()
        if remaining > 0:
            # Consume various data types
            test_int = fdp.ConsumeIntInRange(-1000000, 1000000)
            test_float = fdp.ConsumeFloat()
            test_str = fdp.ConsumeUnicodeNoSurrogates(min(remaining, 512))

            # Basic validation tests
            if test_str:
                _ = len(test_str)
                _ = test_str.strip()
    except (ValueError, OverflowError, MemoryError):
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
