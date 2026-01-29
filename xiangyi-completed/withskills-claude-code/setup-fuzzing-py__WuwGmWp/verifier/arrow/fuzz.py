#!/usr/bin/env python3
"""
Fuzz driver for Arrow library using Atheris (LibFuzzer-based).

Targets:
- DateTimeParser.parse_iso() - ISO 8601 datetime string parsing
- DateTimeParser.parse() - Custom format datetime parsing
- TzinfoParser.parse() - Timezone string parsing
- Arrow.dehumanize() - Humanized relative time parsing
"""

import sys
import atheris


def setup_module():
    """Import the target modules with instrumentation."""
    with atheris.instrument_imports():
        import arrow
        from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    return arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError


# Import modules with instrumentation
arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError = setup_module()


# Pre-create parser instance to avoid overhead
_parser = DateTimeParser()

# Common format strings for parse() testing
FORMAT_STRINGS = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY-MM-DDTHH:mm:ss",
    "YYYY-MM-DDTHH:mm:ssZZ",
    "DD/MM/YYYY",
    "MM-DD-YYYY",
    "MMMM D, YYYY",
    "DD MMM YYYY",
    "X",  # Unix timestamp
    "x",  # Unix timestamp milliseconds
]


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Fuzz entry point that tests arrow parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    # Get the test string from fuzz data
    test_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))

    if not test_string:
        return

    # Test 1: DateTimeParser.parse_iso()
    try:
        _parser.parse_iso(test_string, normalize_whitespace=fdp.ConsumeBool())
    except (ParserError, ParserMatchError, ValueError, OverflowError, OSError):
        # Expected exceptions for invalid input
        pass

    # Test 2: DateTimeParser.parse() with various format strings
    if fdp.remaining_bytes() > 0:
        format_idx = fdp.ConsumeIntInRange(0, len(FORMAT_STRINGS) - 1)
        try:
            _parser.parse(
                test_string,
                FORMAT_STRINGS[format_idx],
                normalize_whitespace=fdp.ConsumeBool()
            )
        except (ParserError, ParserMatchError, ValueError, OverflowError, re.error):
            # Expected exceptions for invalid input
            pass

    # Test 3: TzinfoParser.parse()
    try:
        TzinfoParser.parse(test_string)
    except (ParserError, ValueError, KeyError):
        # Expected exceptions for invalid timezone strings
        pass

    # Test 4: Arrow.dehumanize() - requires an Arrow instance
    if fdp.remaining_bytes() > 0:
        try:
            arw = arrow.utcnow()
            arw.dehumanize(test_string, locale="en_us")
        except (ValueError, KeyError, AttributeError, TypeError):
            # Expected exceptions for invalid humanized strings
            pass

    # Test 5: arrow.get() with string input (main API entry point)
    try:
        arrow.get(test_string)
    except (ParserError, ParserMatchError, ValueError, TypeError, OverflowError, OSError):
        # Expected exceptions for invalid input
        pass


# Import re for exception handling
import re


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
