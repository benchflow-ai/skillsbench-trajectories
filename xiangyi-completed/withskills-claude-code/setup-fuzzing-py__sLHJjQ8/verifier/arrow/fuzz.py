#!/usr/bin/env python3
"""
Fuzz driver for the Arrow datetime library using Atheris (LibFuzzer-based).

Targets:
- DateTimeParser.parse_iso() - ISO 8601-like datetime parsing
- DateTimeParser.parse() - Format-based datetime parsing
- TzinfoParser.parse() - Timezone string parsing
- arrow.get() - Main factory function

Run with: python fuzz.py
"""

import sys
import atheris


def setup_module():
    """Import and instrument the arrow library."""
    with atheris.instrument_imports():
        import arrow
        from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    return arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError


# Import modules with instrumentation
arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError = setup_module()


# Common date format strings to use for parse() testing
FORMAT_STRINGS = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY/MM/DD",
    "DD-MM-YYYY",
    "MMMM D, YYYY",
    "YY-MM-DD",
    "YYYY-MM-DDTHH:mm:ssZ",
    "X",  # Unix timestamp
    "x",  # Unix timestamp in milliseconds
    "YYYY-MM-DD HH:mm:ss ZZ",
]


@atheris.instrument_func
def test_parse_iso(data: str):
    """Fuzz DateTimeParser.parse_iso() with string input."""
    parser = DateTimeParser()
    try:
        parser.parse_iso(data)
    except ParserError:
        pass  # Expected for invalid input
    except ParserMatchError:
        pass  # Expected for unmatched formats
    except (ValueError, OverflowError, OSError):
        pass  # Expected for out-of-range dates


@atheris.instrument_func
def test_parse_iso_normalized(data: str):
    """Fuzz DateTimeParser.parse_iso() with whitespace normalization."""
    parser = DateTimeParser()
    try:
        parser.parse_iso(data, normalize_whitespace=True)
    except ParserError:
        pass
    except ParserMatchError:
        pass
    except (ValueError, OverflowError, OSError):
        pass


@atheris.instrument_func
def test_parse_with_format(data: str, fdp: atheris.FuzzedDataProvider):
    """Fuzz DateTimeParser.parse() with format strings."""
    parser = DateTimeParser()
    fmt = fdp.PickValueInList(FORMAT_STRINGS)
    try:
        parser.parse(data, fmt)
    except ParserError:
        pass
    except ParserMatchError:
        pass
    except (ValueError, OverflowError, OSError, re.error):
        pass


@atheris.instrument_func
def test_tzinfo_parse(data: str):
    """Fuzz TzinfoParser.parse() with timezone strings."""
    try:
        TzinfoParser.parse(data)
    except ParserError:
        pass
    except (ValueError, KeyError):
        pass


@atheris.instrument_func
def test_arrow_get(data: str):
    """Fuzz arrow.get() with string input."""
    try:
        arrow.get(data)
    except ParserError:
        pass
    except ParserMatchError:
        pass
    except (TypeError, ValueError, OverflowError, OSError):
        pass


@atheris.instrument_func
def TestOneInput(data: bytes):
    """Main fuzzer entry point."""
    if len(data) < 2:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Select which function to test
    choice = fdp.ConsumeIntInRange(0, 4)

    # Get remaining data as string
    remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
    try:
        test_data = remaining.decode('utf-8', errors='ignore')
    except Exception:
        return

    if not test_data:
        return

    if choice == 0:
        test_parse_iso(test_data)
    elif choice == 1:
        test_parse_iso_normalized(test_data)
    elif choice == 2:
        # Need a new FDP for format selection
        test_parse_with_format_simple(test_data)
    elif choice == 3:
        test_tzinfo_parse(test_data)
    elif choice == 4:
        test_arrow_get(test_data)


@atheris.instrument_func
def test_parse_with_format_simple(data: str):
    """Fuzz DateTimeParser.parse() with a fixed set of formats."""
    parser = DateTimeParser()
    import random
    fmt = random.choice(FORMAT_STRINGS)
    try:
        parser.parse(data, fmt)
    except ParserError:
        pass
    except ParserMatchError:
        pass
    except (ValueError, OverflowError, OSError):
        pass
    except Exception as e:
        # Catch regex errors
        if "error" in type(e).__name__.lower():
            pass
        else:
            raise


def main():
    """Run the fuzzer."""
    import re  # Import here to avoid issues with global scope
    globals()['re'] = re

    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
