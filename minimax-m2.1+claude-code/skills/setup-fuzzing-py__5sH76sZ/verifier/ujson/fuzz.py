#!/usr/bin/env python3
"""
Fuzz driver for ujson library
Tests JSON encoding/decoding functions
"""

import sys
import atheris
from atheris import FuzzedDataProvider

# Instrument the ujson library
with atheris.instrument_imports():
    import ujson


@atheris.instrument_func
def test_ujson_loads(data):
    """Fuzz ujson.loads() with various JSON strings"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random JSON-like string
        json_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 500))

        if not json_str:
            return

        try:
            result = ujson.loads(json_str)
        except (ValueError, TypeError, ujson.JSONDecodeError):
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_ujson_dumps(data):
    """Fuzz ujson.dumps() with various Python objects"""
    fdp = FuzzedDataProvider(data)

    try:
        # Test with different object types

        # Test with dictionary
        if fdp.ConsumeBool():
            num_items = fdp.ConsumeIntInRange(0, 20)
            test_dict = {}
            for _ in range(num_items):
                key = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 10))
                value = fdp.ConsumeIntInRange(-1000, 1000)
                test_dict[key] = value

            try:
                result = ujson.dumps(test_dict)
            except (TypeError, ValueError):
                pass

        # Test with list
        if fdp.ConsumeBool():
            num_items = fdp.ConsumeIntInRange(0, 20)
            test_list = []
            for _ in range(num_items):
                item = fdp.ConsumeIntInRange(-1000, 1000)
                test_list.append(item)

            try:
                result = ujson.dumps(test_list)
            except (TypeError, ValueError):
                pass

        # Test with string
        if fdp.ConsumeBool():
            test_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))

            try:
                result = ujson.dumps(test_str)
            except (TypeError, ValueError):
                pass

        # Test with number
        if fdp.ConsumeBool():
            test_num = fdp.ConsumeIntInRange(-2**31, 2**31 - 1)

            try:
                result = ujson.dumps(test_num)
            except (TypeError, ValueError):
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_ujson_dumps_params(data):
    """Fuzz ujson.dumps() with various parameters"""
    fdp = FuzzedDataProvider(data)

    try:
        # Create a test object
        test_dict = {"key": "value", "num": 42}

        # Test with ensure_ascii parameter
        if fdp.ConsumeBool():
            try:
                result = ujson.dumps(test_dict, ensure_ascii=fdp.ConsumeBool())
            except (TypeError, ValueError):
                pass

        # Test with indent parameter
        if fdp.ConsumeBool():
            try:
                indent = fdp.ConsumeIntInRange(0, 10)
                result = ujson.dumps(test_dict, indent=indent)
            except (TypeError, ValueError):
                pass

        # Test with sort_keys parameter
        if fdp.ConsumeBool():
            try:
                result = ujson.dumps(test_dict, sort_keys=fdp.ConsumeBool())
            except (TypeError, ValueError):
                pass

        # Test with separators parameter
        if fdp.ConsumeBool():
            try:
                separators = (fdp.ConsumeUnicode(1), fdp.ConsumeUnicode(1))
                result = ujson.dumps(test_dict, separators=separators)
            except (TypeError, ValueError):
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_ujson_loads_nested(data):
    """Fuzz ujson.loads() with nested structures"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate nested JSON-like strings
        json_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 300))

        if not json_str:
            return

        # Test various JSON patterns
        json_patterns = [
            json_str,  # Raw string
            '{"' + json_str[:50] + '": "' + json_str[50:] + '"}',  # Object
            '[' + json_str + ']',  # Array
            '{"nested": {' + json_str[:50] + ': "' + json_str[50:] + '"}}',  # Nested
        ]

        for pattern in json_patterns:
            try:
                result = ujson.loads(pattern)
            except (ValueError, TypeError, ujson.JSONDecodeError):
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_ujson_edge_cases(data):
    """Fuzz ujson with edge cases"""
    fdp = FuzzedDataProvider(data)

    try:
        # Test with empty values
        test_cases = [
            '""',  # Empty string
            '[]',  # Empty array
            '{}',  # Empty object
            'null',  # Null
            'true',  # Boolean true
            'false',  # Boolean false
            '0',  # Zero
            '0.0',  # Float zero
        ]

        for test_case in test_cases:
            try:
                result = ujson.loads(test_case)
            except (ValueError, TypeError, ujson.JSONDecodeError):
                pass

        # Test dumps with edge case values
        edge_values = [
            None,
            True,
            False,
            0,
            0.0,
            "",
            [],
            {},
            float('inf'),
            float('-inf'),
        ]

        for value in edge_values:
            try:
                result = ujson.dumps(value)
            except (TypeError, ValueError, OverflowError):
                pass

    except Exception:
        pass


def TestOneInput(data):
    """Main fuzzing entry point"""
    # Run all test functions
    test_ujson_loads(data)
    test_ujson_dumps(data)
    test_ujson_dumps_params(data)
    test_ujson_loads_nested(data)
    test_ujson_edge_cases(data)


def main():
    """Set up and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
