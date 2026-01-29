#!/usr/bin/env python3
"""
Coverage-guided fuzz driver for the Arrow date/time library.
Uses Atheris for LibFuzzer-style fuzzing.
"""
import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for Arrow date parsing."""
    fdp = atheris.FuzzedDataProvider(data)

    # Import arrow inside the function to ensure instrumentation
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError

    # Generate a string from fuzz input
    test_string = fdp.ConsumeUnicodeNoSurrogates(1024)

    if not test_string:
        return

    # Test 1: arrow.get() with string input
    try:
        arrow.get(test_string)
    except (arrow.ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 2: DateTimeParser.parse_iso()
    parser = DateTimeParser()
    try:
        parser.parse_iso(test_string)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 3: DateTimeParser.parse() with format string
    format_string = fdp.ConsumeUnicodeNoSurrogates(64)
    if format_string:
        try:
            parser.parse(test_string, format_string)
        except (ParserError, ValueError, TypeError, OverflowError, OSError, re.error):
            pass

    # Test 4: TzinfoParser.parse()
    try:
        TzinfoParser.parse(test_string)
    except (ParserError, ValueError, TypeError):
        pass

    # Test 5: arrow.get() with normalize_whitespace
    try:
        arrow.get(test_string, normalize_whitespace=True)
    except (arrow.ParserError, ValueError, TypeError, OverflowError, OSError):
        pass


# Need to import re for the exception handling
import re


def main():
    # Instrument the arrow module for coverage
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
