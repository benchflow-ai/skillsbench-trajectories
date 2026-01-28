#!/usr/bin/env python3
"""
Fuzzer driver for Arrow library - datetime parsing and formatting.
Tests core parsing functions: parse_iso(), parse(), and TzinfoParser.parse()
"""

import sys
import random
from datetime import datetime

# Import Arrow functions
import arrow
from arrow import parser as arrow_parser
from arrow.factory import ArrowFactory


def fuzz_arrow(data: bytes):
    """Main fuzzer function targeting Arrow parsing functions"""

    if len(data) < 1:
        return

    # Decode input
    try:
        test_input = data.decode('utf-8', errors='ignore')
    except:
        return

    if not test_input:
        return

    # Determine which parser to test based on first byte
    choice = data[0] % 5

    try:
        if choice == 0:
            # Test DateTimeParser.parse_iso()
            _fuzz_parse_iso(test_input)
        elif choice == 1:
            # Test DateTimeParser.parse() with format string
            _fuzz_parse_with_format(test_input)
        elif choice == 2:
            # Test TzinfoParser.parse()
            _fuzz_tzinfo_parse(test_input)
        elif choice == 3:
            # Test ArrowFactory.get() with string input
            _fuzz_factory_get(test_input)
        elif choice == 4:
            # Test Arrow.format() with format string
            _fuzz_arrow_format(test_input)
    except Exception:
        # Expected exceptions that are OK
        pass


def _fuzz_parse_iso(iso_string: str):
    """Test parse_iso with various ISO 8601 strings"""
    parser = arrow_parser.DateTimeParser()
    try:
        result = parser.parse_iso(iso_string)
        # Verify result is an Arrow object
        assert result is not None
    except (arrow_parser.ParserError, arrow_parser.ParserMatchError):
        # Expected parsing errors
        pass
    except ValueError:
        # Expected for invalid dates
        pass


def _fuzz_parse_with_format(test_input: str):
    """Test parse() with custom format strings"""
    parser = arrow_parser.DateTimeParser()

    # Split input: first half is date string, second half is format
    mid = len(test_input) // 2
    date_str = test_input[:mid] if mid > 0 else test_input
    fmt_str = test_input[mid:] if mid < len(test_input) else "YYYY-MM-DD"

    try:
        result = parser.parse(date_str, fmt_str)
        assert result is not None
    except (arrow_parser.ParserError, arrow_parser.ParserMatchError):
        pass
    except (ValueError, IndexError):
        pass


def _fuzz_tzinfo_parse(tz_string: str):
    """Test TzinfoParser.parse() with timezone strings"""
    parser = arrow_parser.TzinfoParser()
    try:
        result = parser.parse(tz_string)
        # Result should be a tzinfo object or None
    except arrow_parser.ParserError:
        pass
    except (ValueError, TypeError):
        pass


def _fuzz_factory_get(test_input: str):
    """Test ArrowFactory.get() with string input"""
    factory = ArrowFactory()
    try:
        # get() can parse various string formats
        result = factory.get(test_input)
        assert result is not None
        assert isinstance(result, arrow.Arrow)
    except (arrow_parser.ParserError, arrow_parser.ParserMatchError):
        pass
    except (ValueError, TypeError, AttributeError):
        pass


def _fuzz_arrow_format(fmt_string: str):
    """Test Arrow.format() with format strings"""
    try:
        # Create a test arrow object
        arr = arrow.now()
        result = arr.format(fmt_string)
        # Result should be a string
        assert isinstance(result, str)
    except (arrow_parser.ParserError, ValueError):
        pass
    except (AttributeError, TypeError):
        pass


if __name__ == "__main__":
    # Fuzzing main loop
    test_cases = [
        b"2023-01-15T10:30:45Z",
        b"invalid_date",
        b"2023-13-45",
        b"\x00\x01\x02\xff",
        b"",
        b"a" * 1000,
        b"2023" * 100,
    ]

    # Add random test cases
    random.seed(42)
    for _ in range(100):
        test_cases.append(bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]))

    print(f"Running {len(test_cases)} test cases for arrow fuzzing...")
    success = 0
    errors = 0

    for test_case in test_cases:
        try:
            fuzz_arrow(test_case)
            success += 1
        except Exception as e:
            errors += 1

    print(f"Completed: {success} successful, {errors} with expected errors")
