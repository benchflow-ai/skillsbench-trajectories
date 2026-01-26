#!/usr/bin/env python3
"""
Fuzz driver for ujson library
Focuses on JSON parsing and encoding functions
Targets decode_numeric(), decode_string(), and JSON_DecodeObject()
"""

import atheris
import sys

with atheris.instrument_imports():
    import ujson


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for ujson library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)
    strategy = fdp.ConsumeIntInRange(0, 3)

    if strategy == 0:
        # Fuzz ujson.loads() - main JSON decoder
        try:
            json_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 4096))
            ujson.loads(json_string)
        except (ValueError, TypeError, ujson.JSONDecodeError):
            pass

    elif strategy == 1:
        # Fuzz with bytes input
        try:
            json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 4096))
            ujson.loads(json_bytes)
        except (ValueError, TypeError, ujson.JSONDecodeError, UnicodeDecodeError):
            pass

    elif strategy == 2:
        # Fuzz ujson.dumps() - encoder
        try:
            # Generate various Python objects
            obj_type = fdp.ConsumeIntInRange(0, 4)

            if obj_type == 0:
                # List of integers
                obj = [fdp.ConsumeIntInRange(-1000, 1000)
                       for _ in range(fdp.ConsumeIntInRange(0, 100))]
            elif obj_type == 1:
                # Dict with string keys
                obj = {f'key_{i}': fdp.ConsumeIntInRange(0, 1000)
                       for i in range(fdp.ConsumeIntInRange(0, 50))}
            elif obj_type == 2:
                # Nested structures
                obj = {
                    'nested': [1, 2, 3],
                    'value': fdp.ConsumeFloat(),
                    'bool': fdp.ConsumeBool(),
                }
            else:
                # String value
                obj = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 1024))

            ujson.dumps(obj, ensure_ascii=fdp.ConsumeBool())
        except (ValueError, TypeError, OverflowError):
            pass

    elif strategy == 3:
        # Fuzz numeric parsing with extreme values
        try:
            numeric_tests = [
                fdp.ConsumeFloat(),  # Float
                str(fdp.ConsumeIntInRange(-2**31, 2**31)),  # int32
                str(fdp.ConsumeIntInRange(-2**63, 2**63)),  # int64
                "NaN",
                "Infinity",
                "-Infinity",
                f'1e{fdp.ConsumeIntInRange(-400, 400)}',  # Large exponents
            ]

            for num_test in numeric_tests:
                try:
                    json_str = f'[{num_test}]'
                    ujson.loads(json_str)
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass


if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
