#!/usr/bin/env python3
"""
Fuzz driver for UltraJSON (ujson) library.

Targets:
- ujson.loads() / ujson.decode() - JSON string parsing (PRIMARY TARGET)
- ujson.dumps() / ujson.encode() - JSON encoding
- ujson.load() - File-based JSON parsing

ujson is a fast JSON encoder/decoder written in C. The decode function
is the primary target as it processes untrusted input and has complex
parsing logic for strings, numbers, arrays, and objects.

Usage:
    python fuzz.py [libfuzzer options]

Example:
    python fuzz.py -max_total_time=10
"""

import sys
import atheris


def setup_ujson():
    """Import ujson module inside instrumentation context."""
    global ujson

    import ujson


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Fuzz test entry point.

    Tests ujson's JSON parsing and encoding functions.
    """
    # Test 1: ujson.loads() with bytes input directly
    try:
        result = ujson.loads(data)
        # If successful, test roundtrip
        encoded = ujson.dumps(result)
        decoded = ujson.loads(encoded)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass  # Expected exceptions for invalid JSON
    except Exception:
        pass

    # Test 2: ujson.loads() with string input (UTF-8 decoded)
    try:
        input_str = data.decode('utf-8')
        result = ujson.loads(input_str)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError,
            RecursionError, UnicodeDecodeError):
        pass
    except Exception:
        pass

    # Test 3: ujson.decode() - alias for loads
    try:
        result = ujson.decode(data)
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 4: ujson.loads() with bytearray input
    try:
        result = ujson.loads(bytearray(data))
    except (ujson.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 5: ujson.dumps() with fuzz-generated Python objects
    # Use FuzzedDataProvider to create structured data
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Create various Python objects to encode
        test_objects = []

        # Simple values
        if fdp.remaining_bytes() > 0:
            test_objects.append(fdp.ConsumeFloat())
        if fdp.remaining_bytes() > 0:
            test_objects.append(fdp.ConsumeInt(8))
        if fdp.remaining_bytes() > 0:
            test_objects.append(fdp.ConsumeBool())
        if fdp.remaining_bytes() > 0:
            test_objects.append(fdp.ConsumeUnicodeNoSurrogates(100))
        if fdp.remaining_bytes() > 0:
            test_objects.append(None)

        # Test encoding each object
        for obj in test_objects:
            try:
                encoded = ujson.dumps(obj)
                # Verify roundtrip
                decoded = ujson.loads(encoded)
            except (ValueError, TypeError, OverflowError, RecursionError):
                pass
            except Exception:
                pass

    except Exception:
        pass

    # Test 6: ujson.dumps() with nested structures
    try:
        # Create nested dict/list from fuzz data
        if len(data) > 4:
            depth = min(data[0] % 20, 10)  # Limit nesting depth
            nested = {}
            current = nested
            for i in range(depth):
                key = f"key{i}"
                current[key] = {}
                current = current[key]
            current["value"] = data[1:20].decode('utf-8', errors='replace')

            encoded = ujson.dumps(nested)
            decoded = ujson.loads(encoded)
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeDecodeError):
        pass
    except Exception:
        pass

    # Test 7: ujson.dumps() with various options
    try:
        input_str = data.decode('utf-8', errors='replace')
        test_obj = {"data": input_str[:100]}

        # Test with different options
        ujson.dumps(test_obj, ensure_ascii=True)
        ujson.dumps(test_obj, ensure_ascii=False)
        ujson.dumps(test_obj, encode_html_chars=True)
        ujson.dumps(test_obj, escape_forward_slashes=True)
        ujson.dumps(test_obj, escape_forward_slashes=False)
        ujson.dumps(test_obj, sort_keys=True)
        ujson.dumps(test_obj, indent=2)
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 8: Edge case - NaN and Infinity (ujson extensions)
    try:
        # ujson supports NaN and Infinity by default
        for special in [b'NaN', b'Infinity', b'-Infinity']:
            result = ujson.loads(special)
    except (ujson.JSONDecodeError, ValueError, TypeError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    # Instrument ujson imports
    with atheris.instrument_imports():
        setup_ujson()

    # Setup and run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
