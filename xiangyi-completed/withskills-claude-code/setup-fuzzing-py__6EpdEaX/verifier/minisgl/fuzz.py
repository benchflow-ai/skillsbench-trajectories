#!/usr/bin/env python3
"""Minisgl library fuzzer using Atheris"""

import atheris
import sys
import json

with atheris.instrument_imports():
    from minisgl.message.utils import deserialize_type

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz Minisgl's deserialization functions"""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Generate fuzzed dictionary data
        dict_size = fdp.ConsumeIntInRange(0, 100)

        # Test deserialize_type with various inputs
        try:
            # Create a basic dict structure
            test_dict = {
                "__type__": fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 50)),
                "field1": fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100)),
                "field2": fdp.ConsumeInt(4),
            }

            # Try to deserialize
            try:
                # Use a basic class map
                class_map = {}
                result = deserialize_type(class_map, test_dict)
            except (KeyError, TypeError, ValueError, AttributeError):
                # Expected exceptions for invalid types or missing classes
                pass

        except Exception:
            pass

        # Test with tensor-like structures if enough data
        if len(data) > 20:
            try:
                tensor_dict = {
                    "__type__": "Tensor",
                    "buffer": fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 100)),
                    "dtype": fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 50)),
                }
                class_map = {}
                result = deserialize_type(class_map, tensor_dict)
            except (KeyError, TypeError, ValueError, AttributeError, ImportError):
                # Expected exceptions
                pass

        # Test with nested structures
        if len(data) > 50:
            try:
                nested_dict = {
                    "__type__": fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 50)),
                    "nested": {
                        "__type__": fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 50)),
                        "value": fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 50)),
                    }
                }
                class_map = {}
                result = deserialize_type(class_map, nested_dict)
            except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
                # Expected exceptions
                pass

    except Exception:
        # Catch any unexpected exceptions and report them
        raise

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
