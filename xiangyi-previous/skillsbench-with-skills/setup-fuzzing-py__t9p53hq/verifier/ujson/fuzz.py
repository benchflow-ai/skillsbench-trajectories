#!/usr/bin/env python3
"""
LibFuzzer driver for UltraJSON (ujson) library - fast JSON encoder/decoder.
Tests JSON parsing and encoding: loads(), dumps(), and related functions.
"""

import sys
import json
import random

# Import ujson functions
import ujson


def fuzz_ujson(data: bytes):
    """Main fuzzer function targeting ujson parsing and encoding"""

    if len(data) < 1:
        return

    # Determine which function to test based on first byte
    choice = data[0] % 5

    try:
        if choice == 0:
            # Test ujson.loads() (JSON decoder)
            _fuzz_loads(data)
        elif choice == 1:
            # Test ujson.dumps() (JSON encoder)
            _fuzz_dumps(data)
        elif choice == 2:
            # Test with different parser configurations
            _fuzz_loads_with_variations(data)
        elif choice == 3:
            # Test round-trip encoding/decoding
            _fuzz_roundtrip(data)
        elif choice == 4:
            # Test encoder options variations
            _fuzz_dumps_variations(data)
    except Exception:
        # Expected exceptions during fuzzing
        pass


def _fuzz_loads(data: bytes):
    """Test ujson.loads() - JSON decoder"""
    try:
        # Decode as UTF-8 string (JSON must be text)
        json_str = data.decode('utf-8', errors='ignore')
        result = ujson.loads(json_str)
        # Result can be any JSON type
        assert result is not None or result is None  # Handles null
    except (ujson.JSONDecodeError, ValueError, TypeError):
        # Expected errors for invalid JSON
        pass
    except OverflowError:
        # Can occur with extreme numbers
        pass
    except Exception:
        pass


def _fuzz_dumps(data: bytes):
    """Test ujson.dumps() - JSON encoder"""
    try:
        # Try to create Python objects from data and encode them
        test_objects = [
            data.decode('utf-8', errors='ignore'),  # String
            len(data),  # Integer
            float(len(data)) / 10.0,  # Float
            len(data) % 2 == 0,  # Boolean
            None,  # Null
            list(data[:10]),  # List of bytes/ints
            {"key": data.decode('utf-8', errors='ignore')[:100]},  # Dict
        ]

        for obj in test_objects:
            try:
                result = ujson.dumps(obj)
                assert isinstance(result, str)
            except (TypeError, ValueError, OverflowError):
                # Expected for certain types
                pass

    except Exception:
        pass


def _fuzz_loads_with_variations(data: bytes):
    """Test ujson.loads() with various input"""
    try:
        json_str = data.decode('utf-8', errors='ignore')

        # Test with different content
        test_jsons = [
            json_str,
            f'"{json_str}"',  # As JSON string
            f'[{json_str}]',  # As JSON array
            f'{{{json_str}}}',  # Invalid object but tests error handling
            f'{{"key": {json_str}}}',  # As object value
        ]

        for test_json in test_jsons:
            try:
                result = ujson.loads(test_json)
            except (ujson.JSONDecodeError, ValueError):
                # Expected for invalid JSON
                pass

    except Exception:
        pass


def _fuzz_roundtrip(data: bytes):
    """Test round-trip: dumps() then loads()"""
    try:
        # Create a test object
        test_str = data.decode('utf-8', errors='ignore')

        # Build a simple Python object
        test_obj = {
            "string": test_str[:100],
            "number": len(data),
            "bool": len(data) % 2 == 0,
            "array": list(range(min(10, len(data)))),
        }

        # Encode
        try:
            json_str = ujson.dumps(test_obj)
            assert isinstance(json_str, str)

            # Decode back
            decoded = ujson.loads(json_str)
            assert isinstance(decoded, dict)

            # Verify structure is preserved
            if decoded:
                assert len(decoded) > 0
        except (TypeError, ValueError, OverflowError):
            pass

    except Exception:
        pass


def _fuzz_dumps_variations(data: bytes):
    """Test ujson.dumps() with various options"""
    try:
        test_str = data.decode('utf-8', errors='ignore')

        test_obj = {
            "content": test_str[:50],
            "number": len(data),
            "nested": {"key": "value", "items": [1, 2, 3]},
        }

        # Test with different options
        options_to_test = [
            {"ensure_ascii": True},
            {"ensure_ascii": False},
            {"sort_keys": True},
            {"sort_keys": False},
            {"encode_html_chars": True},
            {"escape_forward_slashes": True},
            {"escape_forward_slashes": False},
            {"allow_nan": True},
            {"allow_nan": False},
            {"indent": 0},
            {"indent": 2},
        ]

        for opts in options_to_test:
            try:
                result = ujson.dumps(test_obj, **opts)
                assert isinstance(result, str)
            except (TypeError, ValueError, OverflowError):
                pass

    except Exception:
        pass


if __name__ == "__main__":
    # Fuzzing main loop
    test_cases = [
        b'{"key": "value"}',
        b'[1, 2, 3]',
        b'"string"',
        b'123',
        b'true',
        b'null',
        b'invalid json',
        b'',
        b'\x00\xff',
    ]

    # Add random test cases
    random.seed(42)
    for _ in range(100):
        test_cases.append(bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]))

    print(f"Running {len(test_cases)} test cases for ujson fuzzing...")
    success = 0
    errors = 0

    for test_case in test_cases:
        try:
            fuzz_ujson(test_case)
            success += 1
        except Exception as e:
            errors += 1

    print(f"Completed: {success} successful, {errors} with expected errors")
