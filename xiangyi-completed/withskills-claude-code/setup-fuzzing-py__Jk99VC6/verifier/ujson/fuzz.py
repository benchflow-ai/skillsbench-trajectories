#!/usr/bin/env python3
"""Fuzz driver for UltraJSON (ujson) library."""

import atheris
import sys

with atheris.instrument_imports():
    import ujson


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for ujson encode/decode."""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Test 1: ujson.loads() with arbitrary bytes/string input
        if len(data) > 0:
            try:
                ujson.loads(data)
            except (ValueError, TypeError, ujson.JSONDecodeError, AttributeError):
                pass

        # Test 2: ujson.loads() with unicode string
        unicode_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 500))
        if len(unicode_input) > 0:
            try:
                ujson.loads(unicode_input)
            except (ValueError, TypeError, ujson.JSONDecodeError):
                pass

        # Test 3: Create and encode various Python objects
        # Generate different types of test data
        test_values = [
            None,
            True,
            False,
            fdp.ConsumeInt(4),
            fdp.ConsumeInt(8),
            fdp.ConsumeFloat(),
            fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100)),
        ]

        for value in test_values:
            try:
                ujson.dumps(value)
            except (TypeError, ValueError, OverflowError):
                pass

        # Test 4: List and dict encoding
        test_list = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))]
        try:
            ujson.dumps(test_list)
        except (TypeError, ValueError):
            pass

        test_dict = {
            "key" + str(i): fdp.ConsumeInt(4)
            for i in range(fdp.ConsumeIntInRange(0, 10))
        }
        try:
            ujson.dumps(test_dict)
        except (TypeError, ValueError):
            pass

        # Test 5: Nested structures
        nested = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "null": None,
            "string": "test",
        }
        try:
            ujson.dumps(nested)
        except (TypeError, ValueError):
            pass

        # Test 6: dumps with various options
        test_obj = {"key": "value", "number": 42}
        encoding_options = [
            {"indent": fdp.ConsumeIntInRange(0, 20)},
            {"ensure_ascii": fdp.ConsumeBool()},
            {"sort_keys": fdp.ConsumeBool()},
        ]
        for options in encoding_options:
            try:
                ujson.dumps(test_obj, **options)
            except (TypeError, ValueError):
                pass

        # Test 7: Round-trip testing (load then dump)
        json_strings = [
            "null",
            "true",
            "false",
            "0",
            "123",
            "-456",
            "1.5",
            '"string"',
            '[]',
            "{}",
            '[1, 2, 3]',
            '{"a": 1}',
        ]
        for json_str in json_strings:
            try:
                obj = ujson.loads(json_str)
                ujson.dumps(obj)
            except (ValueError, TypeError):
                pass

        # Test 8: Edge cases with numeric values
        numeric_edge_cases = [
            0,
            -1,
            1,
            2**31 - 1,
            -(2**31),
            2**63 - 1,
            -(2**63),
            0.0,
            1.5,
            -1.5,
            float('inf'),
            float('-inf'),
            float('nan'),
        ]
        for num in numeric_edge_cases:
            try:
                ujson.dumps(num)
            except (TypeError, ValueError, OverflowError):
                pass

        # Test 9: Unicode handling
        unicode_strings = [
            "hello",
            "你好",
            "🎉",
            "\x00\x01\x02",
            "line1\nline2",
        ]
        for ustr in unicode_strings:
            try:
                ujson.dumps({"text": ustr})
            except (TypeError, ValueError):
                pass

    except Exception:
        # Catch any unexpected exceptions
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
