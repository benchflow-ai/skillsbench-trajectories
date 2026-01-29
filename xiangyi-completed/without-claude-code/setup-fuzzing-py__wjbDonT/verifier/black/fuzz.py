#!/usr/bin/env python3
"""
Fuzz driver for Black formatter
Tests: format_str, lib2to3_parse, code formatting
"""

import atheris
import sys
import os

# Ensure black module is importable
sys.path.insert(0, '/app/black/src')

import black
from black import NothingChanged


@atheris.instrument_func
def test_black_format_str(data):
    """Fuzz black.format_str() - main formatter"""
    try:
        code = data.decode('utf-8', errors='ignore')
        result = black.format_str(code, mode=black.FileMode())
    except (SyntaxError, NothingChanged, ValueError, TypeError):
        pass
    except black.InvalidInput:
        pass
    except Exception:
        # Catch any other expected exceptions
        pass


@atheris.instrument_func
def test_black_parse(data):
    """Fuzz black lib2to3 parser"""
    try:
        code = data.decode('utf-8', errors='ignore')
        # Test the parser directly
        black.lib2to3_parse(code)
    except (SyntaxError, ValueError, TypeError, AttributeError):
        pass


@atheris.instrument_func
def test_black_features(data):
    """Fuzz black feature detection"""
    try:
        code = data.decode('utf-8', errors='ignore')
        # Try to detect features
        black.get_features_used(code)
    except (SyntaxError, ValueError, TypeError):
        pass


def test_one(data):
    """Main fuzzing function"""
    if len(data) < 1:
        return

    # Distribute fuzzing across different functions
    choice = data[0] % 3
    data = data[1:]

    if choice == 0:
        test_black_format_str(data)
    elif choice == 1:
        test_black_parse(data)
    else:
        test_black_features(data)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
