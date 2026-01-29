#!/usr/bin/env python3
"""Fuzz driver for ujson - ultra-fast JSON encoder/decoder"""

import atheris
import sys
import struct

# Import ujson for fuzzing
import ujson


@atheris.instrument_func
def test_one(data):
    """Fuzz driver for ujson decoder"""
    if len(data) < 1:
        return

    # Test 1: ujson.loads with raw bytes
    try:
        # Try as string
        json_str = data.decode('utf-8', errors='ignore')
        if len(json_str) < 10000:
            result = ujson.loads(json_str)
    except (ujson.JSONDecodeError, ValueError, UnicodeDecodeError):
        pass
    except Exception:
        raise

    # Test 2: ujson.loads with bytes input
    try:
        if len(data) < 10000:
            result = ujson.loads(data)
    except (ujson.JSONDecodeError, ValueError, TypeError):
        pass
    except Exception:
        raise

    # Test 3: ujson.loads with bytearray
    try:
        if len(data) < 10000:
            result = ujson.loads(bytearray(data))
    except (ujson.JSONDecodeError, ValueError, TypeError):
        pass
    except Exception:
        raise

    # Test 4: Round-trip test (if loads succeeds)
    try:
        json_str = data.decode('utf-8', errors='ignore')
        if len(json_str) < 10000:
            obj = ujson.loads(json_str)
            # Try to serialize back
            serialized = ujson.dumps(obj)
            # Re-parse to validate
            reparsed = ujson.loads(serialized)
    except (ujson.JSONDecodeError, ValueError, TypeError):
        pass
    except Exception:
        raise

    # Test 5: ujson.dumps with various Python objects
    try:
        # Create test objects from data
        if len(data) >= 4:
            # Test integer serialization
            test_int = struct.unpack('<i', data[:4])[0]
            result = ujson.dumps(test_int)

            # Test float serialization
            if len(data) >= 8:
                test_float = struct.unpack('<d', data[:8])[0]
                result = ujson.dumps(test_float)

            # Test string serialization
            test_str = data.decode('utf-8', errors='ignore')
            result = ujson.dumps(test_str)

            # Test list/dict
            test_list = [test_int, test_str, None, True, False]
            result = ujson.dumps(test_list)

            test_dict = {"key": test_str, "value": test_int}
            result = ujson.dumps(test_dict)
    except (TypeError, ValueError, OverflowError):
        pass
    except Exception:
        raise

    # Test 6: ujson.dumps with options
    try:
        obj = {"test": "value", "num": 42}
        # Test various options
        ujson.dumps(obj, ensure_ascii=True)
        ujson.dumps(obj, ensure_ascii=False)
        ujson.dumps(obj, sort_keys=True)
        ujson.dumps(obj, indent=2)
    except (TypeError, ValueError):
        pass
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
