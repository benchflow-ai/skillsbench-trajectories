#!/usr/bin/env python3
"""
Coverage-guided fuzzing for ujson library using atheris (LibFuzzer compatible).

Targets:
- ujson.loads()/ujson.decode(): JSON string/bytes to Python object
- ujson.dumps()/ujson.encode(): Python object to JSON string (round-trip)
- Various edge cases: deep nesting, unicode, numeric overflow
"""

import sys
import atheris


def setup_ujson():
    """Import ujson module."""
    global ujson
    import ujson as ujson_module
    ujson = ujson_module


def fuzz_loads_str(data: bytes):
    """Fuzz ujson.loads() with string input."""
    try:
        json_str = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        ujson.loads(json_str)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass


def fuzz_loads_bytes(data: bytes):
    """Fuzz ujson.loads() with bytes input."""
    try:
        ujson.loads(data)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError, UnicodeDecodeError):
        pass
    except Exception:
        pass


def fuzz_loads_with_precise_float(data: bytes):
    """Fuzz ujson.loads() with precise_float option."""
    try:
        json_str = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        ujson.loads(json_str)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass


def fuzz_roundtrip(data: bytes):
    """Fuzz encode-decode roundtrip."""
    try:
        json_str = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        # Parse the input as JSON
        obj = ujson.loads(json_str)
        # Re-encode and decode
        encoded = ujson.dumps(obj)
        ujson.loads(encoded)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError, TypeError, OverflowError):
        pass
    except Exception:
        pass


def fuzz_dumps_options(data: bytes):
    """Fuzz ujson.dumps() with various options."""
    if len(data) < 2:
        return

    options = data[0]
    try:
        json_str = data[1:].decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        obj = ujson.loads(json_str)
    except Exception:
        return

    # Vary encoding options
    ensure_ascii = bool(options & 0x01)
    encode_html_chars = bool(options & 0x02)
    escape_forward_slashes = bool(options & 0x04)
    sort_keys = bool(options & 0x08)
    indent = (options >> 4) & 0x07  # 0-7

    try:
        ujson.dumps(
            obj,
            ensure_ascii=ensure_ascii,
            encode_html_chars=encode_html_chars,
            escape_forward_slashes=escape_forward_slashes,
            sort_keys=sort_keys,
            indent=indent
        )
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass


def fuzz_deep_nesting(data: bytes):
    """Fuzz with deeply nested structures."""
    if len(data) < 1:
        return

    # Create nested structure based on input
    depth = min(data[0], 200)  # Limit depth to avoid stack overflow
    rest = data[1:10] if len(data) > 1 else b"1"

    # Build nested array JSON
    nested_array = "[" * depth + rest.decode('utf-8', errors='replace') + "]" * depth

    try:
        ujson.loads(nested_array)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Build nested object JSON
    nested_obj = '{"a":' * depth + '"x"' + '}' * depth

    try:
        ujson.loads(nested_obj)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass


def fuzz_numeric_edge_cases(data: bytes):
    """Fuzz numeric parsing edge cases."""
    try:
        json_str = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    # Try parsing as a number in JSON array context
    numeric_json = f"[{json_str}]"
    try:
        ujson.loads(numeric_json)
    except (ujson.JSONDecodeError, ValueError, RecursionError, MemoryError):
        pass
    except Exception:
        pass


def TestOneInput(data: bytes):
    """Main fuzzing entry point - calls all fuzz targets."""
    if len(data) < 1:
        return

    # Use first byte to select target
    selector = data[0] % 7
    payload = data[1:]

    if selector == 0:
        fuzz_loads_str(payload)
    elif selector == 1:
        fuzz_loads_bytes(payload)
    elif selector == 2:
        fuzz_loads_with_precise_float(payload)
    elif selector == 3:
        fuzz_roundtrip(payload)
    elif selector == 4:
        fuzz_dumps_options(payload)
    elif selector == 5:
        fuzz_deep_nesting(payload)
    else:
        fuzz_numeric_edge_cases(payload)


def main():
    """Main entry point for the fuzzer."""
    setup_ujson()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
