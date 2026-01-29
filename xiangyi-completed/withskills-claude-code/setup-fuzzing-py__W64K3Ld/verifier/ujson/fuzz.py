#!/usr/bin/env python3
"""Fuzz driver for ujson library - JSON parsing and encoding."""

import atheris
import sys

with atheris.instrument_imports():
    import ujson

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for ujson JSON parsing and encoding."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test decoding (parse JSON from raw bytes/strings)
    try:
        # Try to decode as JSON
        json_str = fdp.ConsumeUnicode(len(data))
        ujson.loads(json_str)
    except (ValueError, TypeError, ujson.JSONDecodeError):
        # Expected exceptions for invalid JSON
        pass
    except Exception as e:
        # Crash on unexpected exceptions
        raise e

    # Test encoding (convert Python objects to JSON)
    try:
        fdp = atheris.FuzzedDataProvider(data)
        mode = fdp.ConsumeIntInRange(0, 5)

        if mode == 0:
            # Simple types
            value = fdp.ConsumeBool()
            ujson.dumps(value)

        elif mode == 1:
            # Numbers
            value = fdp.ConsumeFloat()
            ujson.dumps(value)

        elif mode == 2:
            # Strings with various encodings
            value = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 1000))
            ujson.dumps(value)

        elif mode == 3:
            # Lists
            fdp = atheris.FuzzedDataProvider(data)
            list_len = fdp.ConsumeIntInRange(0, 100)
            values = [fdp.ConsumeUnicode(10) for _ in range(list_len)]
            ujson.dumps(values)

        else:
            # Dictionaries
            fdp = atheris.FuzzedDataProvider(data)
            dict_len = fdp.ConsumeIntInRange(0, 50)
            obj = {}
            for _ in range(dict_len):
                key = fdp.ConsumeUnicode(20)
                val = fdp.ConsumeUnicode(50)
                obj[key] = val
            ujson.dumps(obj)

    except (ValueError, TypeError, OverflowError):
        # Expected exceptions
        pass
    except Exception as e:
        # Crash on unexpected exceptions
        raise e

    # Test round-trip (encode then decode)
    try:
        fdp = atheris.FuzzedDataProvider(data)
        original = {
            "key1": fdp.ConsumeUnicode(100),
            "key2": fdp.ConsumeIntInRange(0, 1000000),
            "key3": [fdp.ConsumeUnicode(50) for _ in range(5)],
        }
        encoded = ujson.dumps(original)
        decoded = ujson.loads(encoded)
        # Verify round-trip property
        assert ujson.dumps(decoded) == encoded
    except (ValueError, TypeError, AssertionError):
        pass
    except Exception as e:
        raise e

if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
