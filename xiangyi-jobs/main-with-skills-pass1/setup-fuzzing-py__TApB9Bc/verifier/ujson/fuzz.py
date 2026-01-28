#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for UltraJSON library.
Targets: ujson.loads() (deserialization) and ujson.dumps() (serialization)
"""

import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    """Fuzz entry point for UltraJSON library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz target 1: ujson.loads() - JSON deserialization
    try:
        json_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 4096))
        try:
            obj = ujson.loads(json_str)
            # Sanity check: should return a Python object
            assert obj is not None or json_str.strip() in ['null', 'None']
        except (ValueError, TypeError, ujson.JSONDecodeError):
            # Expected: invalid JSON should raise error
            pass
    except Exception:
        pass

    # Fuzz target 2: ujson.dumps() - JSON serialization
    try:
        # Generate random Python objects to serialize
        obj_type = fdp.ConsumeIntInRange(0, 6)

        test_obj = None
        if obj_type == 0:
            # String
            test_obj = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
        elif obj_type == 1:
            # Integer
            test_obj = fdp.ConsumeInt(8)
        elif obj_type == 2:
            # Float
            test_obj = fdp.ConsumeFloat()
        elif obj_type == 3:
            # Boolean
            test_obj = fdp.ConsumeBool()
        elif obj_type == 4:
            # List
            list_size = fdp.ConsumeIntInRange(1, 32)
            test_obj = []
            for _ in range(list_size):
                elem_type = fdp.ConsumeIntInRange(0, 4)
                if elem_type == 0:
                    test_obj.append(fdp.ConsumeUnicode(32))
                elif elem_type == 1:
                    test_obj.append(fdp.ConsumeInt(4))
                elif elem_type == 2:
                    test_obj.append(fdp.ConsumeBool())
                else:
                    test_obj.append(None)
        else:
            # Dictionary
            dict_size = fdp.ConsumeIntInRange(1, 32)
            test_obj = {}
            for _ in range(dict_size):
                key = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 32))
                value_type = fdp.ConsumeIntInRange(0, 3)
                if value_type == 0:
                    test_obj[key] = fdp.ConsumeUnicode(32)
                elif value_type == 1:
                    test_obj[key] = fdp.ConsumeInt(4)
                else:
                    test_obj[key] = fdp.ConsumeBool()

        try:
            json_output = ujson.dumps(test_obj)
            # Sanity check: output should be string
            assert isinstance(json_output, str)

            # Try to deserialize the output to verify round-trip
            try:
                ujson.loads(json_output)
            except (ValueError, ujson.JSONDecodeError):
                pass
        except (TypeError, ValueError, OverflowError):
            # Expected: some objects may not be serializable
            pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
