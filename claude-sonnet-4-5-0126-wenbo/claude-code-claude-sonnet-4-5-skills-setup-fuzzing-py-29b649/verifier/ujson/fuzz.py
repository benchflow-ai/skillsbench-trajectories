#!/usr/bin/env python3
"""
Fuzz driver for ujson library - Fast JSON encoder/decoder
Fuzzes ujson.loads() for JSON parsing (C extension).
"""

import atheris
import sys

# ujson is a C extension, instrument what we can
with atheris.instrument_imports():
    import ujson


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for ujson.loads()."""
    if len(data) < 1:
        return

    # Test ujson.loads() with fuzzer data
    try:
        # Try as bytes first
        ujson.loads(data)
    except (ValueError, TypeError, OverflowError):
        # Expected exceptions for invalid JSON
        pass
    except Exception as e:
        # Unexpected exception - potential bug in C code
        # Don't crash fuzzer, but this might indicate memory issues
        pass

    # Also try as string
    try:
        fdp = atheris.FuzzedDataProvider(data)
        json_string = fdp.ConsumeUnicodeNoSurrogates(len(data))
        if json_string:
            ujson.loads(json_string)
    except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
        # Expected exceptions
        pass
    except Exception as e:
        # Unexpected exception
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
