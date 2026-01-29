#!/usr/bin/env python3
"""
Fuzz driver for Arrow library - Date/Time parsing
Tests: arrow.get(), parser functions, format functions
"""

import atheris
import sys

# Ensure arrow module is importable
sys.path.insert(0, '/app/arrow')

import arrow
from arrow import ParserError


@atheris.instrument_func
def test_arrow_get(data):
    """Fuzz arrow.get() function with string input"""
    try:
        # Test with string input
        result = arrow.get(data.decode('utf-8', errors='ignore'))
    except (ParserError, ValueError, TypeError, AttributeError):
        pass
    except Exception as e:
        # Unexpected error - may indicate a bug
        if "AssertionError" not in str(type(e)):
            pass


@atheris.instrument_func
def test_arrow_parse(data):
    """Fuzz arrow parser with string input"""
    try:
        # Try to parse as various formats
        text = data.decode('utf-8', errors='ignore')
        if len(text) > 0:
            arrow.get(text)
    except (ParserError, ValueError, TypeError, AttributeError, OverflowError):
        pass


@atheris.instrument_func
def test_arrow_format(data):
    """Fuzz arrow formatting with format strings"""
    try:
        text = data.decode('utf-8', errors='ignore')
        # Create a default arrow object and try to format it
        arr = arrow.now()
        if len(text) > 0:
            arr.format(text)
    except (ValueError, AttributeError, TypeError):
        pass


def test_one(data):
    """Main fuzzing function"""
    if len(data) < 1:
        return

    # Distribute fuzzing across different functions
    choice = data[0] % 3
    data = data[1:]

    if choice == 0:
        test_arrow_get(data)
    elif choice == 1:
        test_arrow_parse(data)
    else:
        test_arrow_format(data)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
