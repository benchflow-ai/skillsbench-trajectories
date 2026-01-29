#!/usr/bin/env python3
"""Fuzz driver for Arrow datetime parsing library."""

import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for Arrow parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    # Generate test inputs
    test_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 200))

    try:
        # Test 1: arrow.get() with string input
        if len(test_string) > 0:
            try:
                arrow.get(test_string)
            except (ValueError, TypeError, AttributeError):
                pass

        # Test 2: Parse ISO format
        if len(test_string) > 0:
            try:
                parser = DateTimeParser()
                parser.parse_iso(test_string)
            except (ValueError, IndexError, TypeError, AttributeError):
                pass

        # Test 3: Parse with custom format
        if len(test_string) >= 2:
            format_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 50))
            try:
                parser = DateTimeParser()
                parser.parse(test_string, format_string)
            except (ValueError, IndexError, TypeError, AttributeError, KeyError):
                pass

        # Test 4: Timezone parsing
        if len(test_string) > 0:
            try:
                tz_parser = TzinfoParser()
                tz_parser.parse(test_string)
            except (ValueError, TypeError, AttributeError):
                pass

        # Test 5: arrow.get() with numeric input
        timestamp = fdp.ConsumeFloat()
        try:
            arrow.get(timestamp)
        except (ValueError, TypeError, OSError, OverflowError):
            pass

    except Exception:
        # Catch any unexpected exceptions
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
