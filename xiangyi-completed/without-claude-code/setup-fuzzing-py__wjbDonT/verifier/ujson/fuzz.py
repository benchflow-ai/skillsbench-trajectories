#!/usr/bin/env python3
"""
Fuzz driver for ujson - Ultra-fast JSON encoder/decoder
Tests: loads(), dumps(), parsing, serialization
"""

import atheris
import sys
import json

# Try to import ujson - it may need to be built first
try:
    import ujson
    UJSON_AVAILABLE = True
except ImportError:
    UJSON_AVAILABLE = False
    ujson = None


@atheris.instrument_func
def test_ujson_loads(data):
    """Fuzz ujson.loads() - JSON string parsing"""
    if not UJSON_AVAILABLE:
        return

    try:
        json_str = data.decode('utf-8', errors='ignore')
        ujson.loads(json_str)
    except (ValueError, TypeError, ujson.JSONDecodeError if hasattr(ujson, 'JSONDecodeError') else ValueError):
        pass
    except Exception as e:
        # Catch unexpected exceptions
        if "JSONDecode" not in str(type(e)):
            pass


@atheris.instrument_func
def test_ujson_dumps(data):
    """Fuzz ujson.dumps() - Object serialization"""
    if not UJSON_AVAILABLE:
        return

    try:
        # Try to parse as JSON first, then serialize
        json_str = data.decode('utf-8', errors='ignore')
        obj = ujson.loads(json_str)
        ujson.dumps(obj)
    except (ValueError, TypeError):
        pass


@atheris.instrument_func
def test_json_round_trip(data):
    """Fuzz JSON encoding/decoding round trips"""
    if not UJSON_AVAILABLE:
        return

    try:
        json_str = data.decode('utf-8', errors='ignore')
        # Load and re-encode
        obj = ujson.loads(json_str)
        result = ujson.dumps(obj)
        # Try to load again
        ujson.loads(result)
    except (ValueError, TypeError):
        pass


def test_one(data):
    """Main fuzzing function"""
    if len(data) < 1:
        return

    if not UJSON_AVAILABLE:
        return

    # Distribute fuzzing across different functions
    choice = data[0] % 3
    data = data[1:]

    if choice == 0:
        test_ujson_loads(data)
    elif choice == 1:
        test_ujson_dumps(data)
    else:
        test_json_round_trip(data)


if __name__ == "__main__":
    if UJSON_AVAILABLE:
        atheris.Setup(sys.argv, test_one)
        atheris.Fuzz()
    else:
        print("ujson not available, fuzzer cannot run", file=sys.stderr)
        sys.exit(1)
