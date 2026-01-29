#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for arrow library.
Tests arrow's parser, formatter, and API functions with fuzzed input.
"""

import sys
import atheris
import arrow
from arrow import parser as arrow_parser
from arrow.parser import ParserError


def __test_one_input(data: bytes) -> None:
    """Fuzz driver for arrow library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Split fuzzed data into parts for different test strategies
    action = fdp.ConsumeIntInRange(0, 7)

    if action == 0:
        # Test arrow.get() with string input
        try:
            datetime_str = fdp.ConsumeUnicode(256)
            arrow.get(datetime_str)
        except (ValueError, ParserError, TypeError, OverflowError):
            pass

    elif action == 1:
        # Test arrow.get() with numeric timestamp
        try:
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)
        except (ValueError, TypeError, OSError, OverflowError):
            pass

    elif action == 2:
        # Test arrow.get() with format string
        try:
            datetime_str = fdp.ConsumeUnicode(256)
            fmt_str = fdp.ConsumeUnicode(128)
            arrow.get(datetime_str, fmt_str)
        except (ValueError, ParserError, TypeError, IndexError):
            pass

    elif action == 3:
        # Test DateTimeParser.parse_iso()
        try:
            dt_parser = arrow_parser.DateTimeParser()
            datetime_str = fdp.ConsumeUnicode(256)
            normalize = fdp.ConsumeBool()
            dt_parser.parse_iso(datetime_str, normalize_whitespace=normalize)
        except (ValueError, ParserError, TypeError, AttributeError):
            pass

    elif action == 4:
        # Test DateTimeFormatter.format()
        try:
            fmt = fdp.ConsumeUnicode(256)
            arrow_instance = arrow.utcnow()
            arrow_instance.format(fmt)
        except (ValueError, ParserError, TypeError):
            pass

    elif action == 5:
        # Test TzinfoParser.parse()
        try:
            tz_parser = arrow_parser.TzinfoParser()
            tz_str = fdp.ConsumeUnicode(64)
            tz_parser.parse(tz_str)
        except (ValueError, ParserError, TypeError):
            pass

    elif action == 6:
        # Test Arrow.strptime()
        try:
            datetime_str = fdp.ConsumeUnicode(256)
            fmt_str = fdp.ConsumeUnicode(128)
            arrow.Arrow.strptime(datetime_str, fmt_str)
        except (ValueError, ParserError, TypeError, IndexError):
            pass

    elif action == 7:
        # Test arrow.get() with multiple args
        try:
            year = fdp.ConsumeIntInRange(1, 9999)
            month = fdp.ConsumeIntInRange(1, 12)
            day = fdp.ConsumeIntInRange(1, 31)
            arrow.get(year, month, day)
        except (ValueError, TypeError, OverflowError):
            pass


# Initialize atheris for code coverage guidance
atheris.Setup(sys.argv, __test_one_input)

if __name__ == "__main__":
    atheris.Fuzz()
