#!/usr/bin/env python3
"""
Fuzz driver for ujson library using atheris.

Tests:
- ujson.dumps() with various Python objects
- ujson.loads() with malformed JSON
- JSON parsing edge cases
"""

import sys
import atheris
from typing import List


def fuzz_ujson_loads(data: bytes) -> None:
    """Fuzz ujson.loads() with various JSON inputs."""
    try:
        import ujson

        # Decode input to string
        if len(data) > 0:
            try:
                json_str = data.decode('utf-8', errors='ignore')
            except Exception:
                return

            # Test loads with various inputs
            try:
                result = ujson.loads(json_str)
            except (ValueError, TypeError, OverflowError):
                pass  # Expected for malformed JSON

    except ImportError:
        pass


def fuzz_ujson_dumps(data: bytes) -> None:
    """Fuzz ujson.dumps() with various Python objects."""
    try:
        import ujson

        # Create various test objects based on data
        obj = None

        if len(data) == 0:
            obj = None
        elif len(data) < 4:
            # Small integers
            obj = len(data)
        elif len(data) < 10:
            # String
            obj = data.decode('utf-8', errors='ignore')
        elif len(data) < 20:
            # List
            obj = list(data[:10])
        else:
            # Dictionary
            obj = {
                'key1': data[:5].decode('utf-8', errors='ignore'),
                'key2': list(data[5:15]),
                'key3': len(data)
            }

        try:
            result = ujson.dumps(obj)
        except (TypeError, ValueError, OverflowError):
            pass  # Expected for invalid types

    except ImportError:
        pass


def fuzz_ujson_comprehensive(data: bytes) -> None:
    """Comprehensive fuzzing for ujson."""
    try:
        import ujson

        if len(data) == 0:
            return

        # Test with various input types
        json_str = data.decode('utf-8', errors='ignore')

        # Test loads
        try:
            ujson.loads(json_str)
        except Exception:
            pass

        # Test with numeric strings
        if data[0] < 128:
            try:
                num_str = str(len(data))
                ujson.loads(num_str)
            except Exception:
                pass

        # Test with array-like strings
        if len(data) > 2:
            try:
                arr_str = '[' + ','.join(str(b % 10) for b in data[:10]) + ']'
                ujson.loads(arr_str)
            except Exception:
                pass

        # Test with object-like strings
        if len(data) > 4:
            try:
                obj_str = '{"a":' + str(data[0]) + ',"b":"test"}'
                ujson.loads(obj_str)
            except Exception:
                pass

    except ImportError:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing entry point."""
    fuzz_ujson_loads(data)
    fuzz_ujson_dumps(data)
    fuzz_ujson_comprehensive(data)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Fuzz driver for ujson library")
        print("Usage: python fuzz.py")
        sys.exit(0)

    atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
    atheris.Fuzz()
