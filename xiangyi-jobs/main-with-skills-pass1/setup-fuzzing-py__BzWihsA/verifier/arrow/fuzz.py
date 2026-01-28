#!/usr/bin/env python3
"""Fuzz driver for Arrow library - date/time parsing"""

import atheris
import sys

with atheris.instrument_imports():
    import arrow

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz arrow.get() with various date/time string inputs"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test arrow.get() with random strings
    try:
        date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
        if date_string:
            arrow.get(date_string)
    except (arrow.parser.ParserError, ValueError, OverflowError, TypeError):
        # Expected exceptions for invalid inputs
        pass
    except Exception as e:
        # Catch any unexpected exceptions
        if "Invalid" not in str(e) and "Cannot" not in str(e):
            raise

    # Test with format strings
    try:
        remaining = fdp.remaining_bytes()
        if remaining > 2:
            date_str = fdp.ConsumeUnicodeNoSurrogates(remaining // 2)
            format_str = fdp.ConsumeUnicodeNoSurrogates(remaining // 2)
            if date_str and format_str:
                arrow.get(date_str, format_str)
    except (arrow.parser.ParserError, ValueError, OverflowError, TypeError, AttributeError):
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
