#!/usr/bin/env python3
"""
Fuzz driver for Arrow library - datetime parsing and formatting
Focuses on arrow.get() which is the main parsing function
"""
import sys
import atheris

# Import after atheris for better instrumentation
with atheris.instrument_imports():
    import arrow
    from arrow import ParserError


def TestOneInput(data):
    """Fuzz arrow.get() and related parsing functions"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Parse string as datetime
    datetime_str = fdp.ConsumeUnicodeNoSurrogates(200)
    try:
        result = arrow.get(datetime_str)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        # Expected exceptions for invalid input
        pass

    # Test 2: Parse with format string
    if fdp.remaining_bytes() > 20:
        datetime_str = fdp.ConsumeUnicodeNoSurrogates(100)
        format_str = fdp.ConsumeUnicodeNoSurrogates(50)
        try:
            result = arrow.get(datetime_str, format_str)
        except (ParserError, ValueError, TypeError, AttributeError, KeyError, OverflowError, OSError):
            # Expected exceptions
            pass

    # Test 3: Format string fuzzing (if we got a valid arrow object)
    if fdp.remaining_bytes() > 10:
        format_str = fdp.ConsumeUnicodeNoSurrogates(50)
        try:
            # Use a known valid arrow object
            now = arrow.now()
            result = now.format(format_str)
        except (ValueError, TypeError, KeyError, AttributeError):
            # Expected exceptions for invalid format strings
            pass

    # Test 4: Parse timestamp
    if fdp.remaining_bytes() > 4:
        try:
            timestamp = fdp.ConsumeInt(8)
            result = arrow.get(timestamp)
        except (ValueError, TypeError, OverflowError, OSError):
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
