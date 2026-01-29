#!/usr/bin/env python3
"""
Fuzz driver for Arrow library
Tests important date/time parsing and formatting functions
"""

import sys
import atheris
from atheris import FuzzedDataProvider

# Instrument the arrow library
with atheris.instrument_imports():
    import arrow
    from dateutil import parser


@atheris.instrument_func
def test_arrow_get(data):
    """Fuzz arrow.get() with various input types"""
    fdp = FuzzedDataProvider(data)

    try:
        # Test with string input
        if fdp.ConsumeBool():
            date_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))
            try:
                result = arrow.get(date_string)
            except (ValueError, parser.ParserError):
                pass

        # Test with integer timestamp
        if fdp.ConsumeBool():
            timestamp = fdp.ConsumeIntInRange(0, 2**31 - 1)
            try:
                result = arrow.get(timestamp)
            except (ValueError, OSError):
                pass

        # Test with float timestamp
        if fdp.ConsumeBool():
            timestamp = fdp.ConsumeFloat()
            try:
                result = arrow.get(timestamp)
            except (ValueError, OSError):
                pass

        # Test with format string
        if fdp.ConsumeBool():
            date_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 50))
            fmt_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 50))
            try:
                result = arrow.get(date_string, fmt_string)
            except (ValueError, parser.ParserError, KeyError):
                pass

        # Test arrow.now() and utcnow()
        result = arrow.now()
        result = arrow.utcnow()

    except Exception:
        # Catch any unexpected errors
        pass


@atheris.instrument_func
def test_arrow_format(data):
    """Fuzz Arrow formatting functions"""
    fdp = FuzzedDataProvider(data)

    try:
        # Create a simple arrow instance
        arr = arrow.get("2023-01-01")

        # Test formatting with various format strings
        if fdp.ConsumeBool():
            fmt = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 50))
            try:
                result = arr.format(fmt)
            except ValueError:
                pass

        # Test format with built-in constants
        try:
            result = arr.format(arrow.FORMAT_RFC2822)
        except Exception:
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_arrow_manipulation(data):
    """Fuzz Arrow date/time manipulation"""
    fdp = FuzzedDataProvider(data)

    try:
        arr = arrow.get("2023-01-01")

        # Test replace
        if fdp.ConsumeBool():
            year = fdp.ConsumeIntInRange(1, 9999)
            try:
                result = arr.replace(year=year)
            except ValueError:
                pass

        # Test shift
        if fdp.ConsumeBool():
            try:
                result = arr.shift(weeks=fdp.ConsumeIntInRange(-10, 10))
            except Exception:
                pass

        # Test to timezone
        if fdp.ConsumeBool():
            try:
                result = arr.to("UTC")
            except Exception:
                pass

    except Exception:
        pass


def TestOneInput(data):
    """Main fuzzing entry point"""
    # Run all test functions
    test_arrow_get(data)
    test_arrow_format(data)
    test_arrow_manipulation(data)


def main():
    """Set up and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
