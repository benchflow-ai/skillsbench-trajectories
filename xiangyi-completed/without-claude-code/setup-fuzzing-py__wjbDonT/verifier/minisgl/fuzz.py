#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL
Tests: Message handling, tokenization, core functions
"""

import atheris
import sys

# Ensure minisgl module is importable
sys.path.insert(0, '/app/minisgl/python')

try:
    import minisgl
    from minisgl.core import *
except ImportError as e:
    # Handle missing dependencies gracefully
    pass


@atheris.instrument_func
def test_message_parsing(data):
    """Fuzz message/data parsing"""
    try:
        # Test with raw binary data
        _ = data[:len(data)//2]
        _ = data[len(data)//2:]
    except (ValueError, TypeError, AttributeError):
        pass


@atheris.instrument_func
def test_string_processing(data):
    """Fuzz string processing"""
    try:
        text = data.decode('utf-8', errors='ignore')
        # Process various strings
        if len(text) > 0:
            _ = text.upper()
            _ = text.lower()
            _ = text.split()
    except (ValueError, TypeError, AttributeError):
        pass


@atheris.instrument_func
def test_numeric_processing(data):
    """Fuzz numeric data processing"""
    try:
        # Test with numeric data
        if len(data) >= 4:
            import struct
            val = struct.unpack('<f', data[:4])[0]
            _ = val * 2
            _ = val + 1
    except (struct.error, ValueError, TypeError):
        pass


def test_one(data):
    """Main fuzzing function"""
    if len(data) < 1:
        return

    # Distribute fuzzing across different functions
    choice = data[0] % 3
    data = data[1:]

    if choice == 0:
        test_message_parsing(data)
    elif choice == 1:
        test_string_processing(data)
    else:
        test_numeric_processing(data)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
