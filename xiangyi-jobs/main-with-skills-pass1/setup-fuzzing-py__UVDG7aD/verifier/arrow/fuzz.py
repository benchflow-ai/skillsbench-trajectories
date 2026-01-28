#!/usr/bin/env python3
"""
Atheris-based fuzz driver for the Arrow datetime library.

This fuzzer targets the key parsing functions:
1. DateTimeParser.parse_iso() - Primary ISO 8601 parsing
2. DateTimeParser.parse() - Format-based parsing
3. TzinfoParser.parse() - Timezone string parsing
4. ArrowFactory.get() - Main entry point

Run with:
    python fuzz.py [-atheris_runs=10000]

For coverage-guided fuzzing, run without the runs limit.
"""

import sys
import atheris


def setup_arrow():
    """Import arrow modules inside instrumentation context."""
    global arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError


# Instrument imports
with atheris.instrument_imports():
    setup_arrow()


# Common format strings for parse() testing
FORMAT_STRINGS = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY/MM/DD",
    "DD-MM-YYYY",
    "YYYY-MM-DDTHH:mm:ssZ",
    "YYYY-MM-DD HH:mm:ss ZZ",
    "YY-MM-DD",
    "MMMM DD, YYYY",
    "MMM D, YYYY",
    "DD/MM/YYYY HH:mm",
    "X",  # Unix timestamp
    "x",  # Expanded timestamp
    "W",  # Week date
    "YYYY-DDDD",  # Day of year
]


@atheris.instrument_func
def test_parse_iso(data: bytes) -> None:
    """Fuzz DateTimeParser.parse_iso() with arbitrary strings."""
    try:
        # Convert bytes to string, handling potential decode errors
        datetime_string = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return

    parser = DateTimeParser()

    # Test parse_iso without whitespace normalization
    try:
        parser.parse_iso(datetime_string, normalize_whitespace=False)
    except (ParserError, ParserMatchError, ValueError, OverflowError, OSError):
        # Expected exceptions for invalid input
        pass
    except RecursionError:
        # Can happen with deeply nested input
        pass

    # Test parse_iso with whitespace normalization
    try:
        parser.parse_iso(datetime_string, normalize_whitespace=True)
    except (ParserError, ParserMatchError, ValueError, OverflowError, OSError):
        pass
    except RecursionError:
        pass


@atheris.instrument_func
def test_parse_with_format(data: bytes) -> None:
    """Fuzz DateTimeParser.parse() with format strings."""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        datetime_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 200))
    except Exception:
        return

    parser = DateTimeParser()

    # Test with each predefined format string
    for fmt in FORMAT_STRINGS:
        try:
            parser.parse(datetime_string, fmt, normalize_whitespace=False)
        except (ParserError, ParserMatchError, ValueError, OverflowError, OSError):
            pass
        except RecursionError:
            pass

    # Test with fuzzed format string
    try:
        fuzz_format = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 50))
        parser.parse(datetime_string, fuzz_format, normalize_whitespace=False)
    except (ParserError, ParserMatchError, ValueError, OverflowError, OSError, re.error):
        pass
    except RecursionError:
        pass

    # Test with list of formats
    try:
        parser.parse(datetime_string, FORMAT_STRINGS, normalize_whitespace=False)
    except (ParserError, ParserMatchError, ValueError, OverflowError, OSError):
        pass
    except RecursionError:
        pass


@atheris.instrument_func
def test_tzinfo_parse(data: bytes) -> None:
    """Fuzz TzinfoParser.parse() with timezone strings."""
    try:
        tzinfo_string = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return

    try:
        TzinfoParser.parse(tzinfo_string)
    except (ParserError, ValueError, KeyError, OverflowError, OSError):
        # Expected exceptions for invalid timezone
        pass


@atheris.instrument_func
def test_arrow_get(data: bytes) -> None:
    """Fuzz arrow.get() with various inputs."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test with string input
    try:
        string_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 200))
        arrow.get(string_input)
    except (ParserError, ParserMatchError, ValueError, TypeError, OverflowError, OSError):
        pass
    except RecursionError:
        pass

    # Test with numeric input (timestamp)
    try:
        if fdp.ConsumeBool():
            # Float timestamp
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)
        else:
            # Integer timestamp
            timestamp = fdp.ConsumeInt(8)
            arrow.get(timestamp)
    except (ValueError, TypeError, OverflowError, OSError):
        pass

    # Test with tuple input (iso calendar)
    try:
        year = fdp.ConsumeIntInRange(-10000, 10000)
        week = fdp.ConsumeIntInRange(-100, 100)
        day = fdp.ConsumeIntInRange(-100, 100)
        arrow.get((year, week, day))
    except (ValueError, TypeError, OverflowError, OSError):
        pass


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Main fuzzing entry point."""
    if len(data) < 2:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Select which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)
    remaining_data = fdp.ConsumeBytes(fdp.remaining_bytes())

    if choice == 0:
        test_parse_iso(remaining_data)
    elif choice == 1:
        test_parse_with_format(remaining_data)
    elif choice == 2:
        test_tzinfo_parse(remaining_data)
    else:
        test_arrow_get(remaining_data)


# Need to import re for exception handling
import re


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
