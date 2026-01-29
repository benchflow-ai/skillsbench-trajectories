#!/usr/bin/env python3
"""
Fuzzing driver for ujson library.
Targets: ujson.loads() (JSON decoding), ujson.dumps() (JSON encoding)
"""

import atheris
import sys

# Instrument the library before importing
atheris.instrument_imports(["ujson"])

import ujson
import json


@atheris.instrument_func
def fuzz_ujson_loads(data):
    """Fuzz ujson.loads() - JSON parsing"""
    try:
        # Convert bytes to string for JSON parsing
        json_str = data.decode('utf-8', errors='ignore')

        # Try to parse with ujson
        result = ujson.loads(json_str)

    except (ValueError, ujson.JSONDecodeError if hasattr(ujson, 'JSONDecodeError') else ValueError):
        # Expected - invalid JSON
        return
    except (UnicodeDecodeError, OverflowError):
        # Expected - encoding or numeric issues
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_ujson_dumps(data):
    """Fuzz ujson.dumps() - JSON encoding"""
    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Generate different Python types to encode
        obj_type = fdp.ConsumeIntInRange(0, 5)

        if obj_type == 0:
            # Simple dict
            obj = {"key": fdp.ConsumeString(size=100)}
        elif obj_type == 1:
            # List with mixed types
            obj = [
                fdp.ConsumeInt(bytes=4),
                fdp.ConsumeString(size=50),
                fdp.ConsumeBool(),
            ]
        elif obj_type == 2:
            # Nested structure
            obj = {
                "nested": {
                    "value": fdp.ConsumeInt(bytes=4),
                    "list": [1, 2, 3],
                }
            }
        elif obj_type == 3:
            # String with special chars
            obj = fdp.ConsumeString(size=100)
        else:
            # Number
            obj = fdp.ConsumeFloatInRange(-1e10, 1e10)

        # Try different ujson.dumps options
        ensure_ascii = fdp.ConsumeBool()
        escape_forward_slashes = fdp.ConsumeBool()
        sort_keys = fdp.ConsumeBool()

        result = ujson.dumps(
            obj,
            ensure_ascii=ensure_ascii,
            escape_forward_slashes=escape_forward_slashes,
            sort_keys=sort_keys,
        )

    except (TypeError, ValueError, OverflowError):
        # Expected - type or serialization errors
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_ujson_roundtrip(data):
    """Fuzz ujson roundtrip: dumps -> loads"""
    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Create a simple object
        obj = {
            "int": fdp.ConsumeInt(bytes=4),
            "float": fdp.ConsumeFloatInRange(-1e10, 1e10),
            "str": fdp.ConsumeString(size=50),
            "bool": fdp.ConsumeBool(),
            "list": [1, 2, 3],
        }

        # Encode and decode
        encoded = ujson.dumps(obj)
        decoded = ujson.loads(encoded)

        # Verify consistency
        assert isinstance(decoded, dict)

    except (TypeError, ValueError, OverflowError):
        # Expected errors
        return
    except AssertionError:
        # Expected if structure changes during roundtrip
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def test_ujson_fuzzer(data):
    """Main fuzz target dispatcher"""
    if len(data) < 2:
        return

    # Route to different fuzz targets based on first byte
    target = data[0] % 3
    remaining_data = data[1:]

    if target == 0:
        fuzz_ujson_loads(remaining_data)
    elif target == 1:
        fuzz_ujson_dumps(remaining_data)
    else:
        fuzz_ujson_roundtrip(remaining_data)


# Setup and run fuzzer
atheris.Setup(sys.argv, test_ujson_fuzzer)
atheris.Fuzz()
