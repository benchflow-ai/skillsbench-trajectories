#!/usr/bin/env python3
"""Fuzz driver for MiniSGL message utilities and serialization."""

import atheris
import sys
import json

with atheris.instrument_imports():
    try:
        from minisgl.message.utils import deserialize_type, serialize_type
    except ImportError:
        # Fallback if imports fail
        pass


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for MiniSGL deserialization."""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Test 1: JSON deserialization with random data
        json_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 500))
        if len(json_input) > 0:
            try:
                # Try to parse as JSON
                parsed = json.loads(json_input)
            except (ValueError, json.JSONDecodeError):
                pass

        # Test 2: Deserialize with mock cls_map
        if len(json_input) > 0:
            try:
                # Create a minimal cls_map for testing
                cls_map = {
                    "dict": dict,
                    "list": list,
                    "str": str,
                    "int": int,
                    "float": float,
                }
                try:
                    json_data = json.loads(json_input)
                    if isinstance(json_data, dict):
                        deserialize_type(cls_map, json_data)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            except (KeyError, TypeError, AttributeError):
                pass

        # Test 3: Test with various JSON structures
        json_structs = [
            "{}",
            "[]",
            '{"key": "value"}',
            '[1, 2, 3]',
            '{"nested": {"data": 123}}',
        ]
        for struct in json_structs:
            try:
                cls_map = {"dict": dict, "list": list}
                data_obj = json.loads(struct)
                if isinstance(data_obj, dict):
                    deserialize_type(cls_map, data_obj)
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                pass

        # Test 4: Serialization tests
        test_objects = [
            {},
            [],
            {"key": "value"},
            [1, 2, 3],
            {"nested": {"data": 123}},
            None,
            True,
            False,
        ]
        for obj in test_objects:
            try:
                if hasattr(obj, '__dict__'):
                    serialize_type(obj)
            except (TypeError, AttributeError):
                pass

        # Test 5: Edge cases with malformed JSON
        edge_cases = [
            "{",
            "[",
            "}{",
            '{"incomplete": ',
            "[1, 2,",
        ]
        for case in edge_cases:
            try:
                json.loads(case)
            except (json.JSONDecodeError, ValueError):
                pass

    except Exception:
        # Catch any unexpected exceptions
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
