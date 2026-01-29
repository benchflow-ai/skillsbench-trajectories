"""
Fuzz driver for ujson library - Fast JSON encoder/decoder.
Coverage-guided fuzzing using atheris/pythonfuzz pattern.
"""

import sys
import math

# Add ujson to path
sys.path.insert(0, '/app/ujson/src')

import ujson


def validate_utf8(data: bytes) -> bool:
    """Check if data is valid UTF-8."""
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def safe_unicode_decode(data: bytes) -> str:
    """Safely decode bytes to string."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('utf-8', errors='replace')


def fuzz_loads_basic(data: bytes) -> None:
    """Fuzz basic JSON parsing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        result = ujson.loads(input_str)
    except (ValueError, ujson.JSONDecodeError, TypeError, OverflowError):
        pass


def fuzz_loads_bytes(data: bytes) -> None:
    """Fuzz JSON parsing with bytes input."""
    try:
        result = ujson.loads(data)
    except (ValueError, ujson.JSONDecodeError, TypeError, OverflowError):
        pass


def fuzz_loads_precise_float(data: bytes) -> None:
    """Fuzz JSON parsing with precise_float option."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        result = ujson.loads(input_str, precise_float=True)
    except (ValueError, ujson.JSONDecodeError, TypeError, OverflowError):
        pass


def fuzz_dumps_basic(data: bytes) -> None:
    """Fuzz basic JSON encoding."""
    input_str = safe_unicode_decode(data)

    try:
        # Try to decode as JSON first
        obj = ujson.loads(input_str)
        result = ujson.dumps(obj)
    except (ValueError, ujson.JSONDecodeError, TypeError, OverflowError):
        # If not valid JSON, try direct string encoding
        try:
            result = ujson.dumps(input_str)
        except (TypeError, OverflowError):
            pass


def fuzz_dumps_params(data: bytes) -> None:
    """Fuzz JSON encoding with various parameters."""
    input_str = safe_unicode_decode(data)

    try:
        obj = ujson.loads(input_str) if input_str.startswith(('{', '[')) else input_str
    except (ValueError, ujson.JSONDecodeError):
        obj = input_str

    # Test with various parameters
    param_sets = [
        {'ensure_ascii': True},
        {'ensure_ascii': False},
        {'indent': 0},
        {'indent': 2},
        {'allow_nan': True},
    ]

    for params in param_sets:
        try:
            result = ujson.dumps(obj, **params)
        except (TypeError, OverflowError, ValueError):
            pass


def fuzz_nested_structures(data: bytes) -> None:
    """Fuzz deeply nested JSON structures."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        result = ujson.loads(input_str)
        # Recursively check depth
        def check_depth(obj, depth=0):
            if depth > 100:
                raise RecursionError
            if isinstance(obj, dict):
                for v in obj.values():
                    check_depth(v, depth + 1)
            elif isinstance(obj, list):
                for v in obj:
                    check_depth(v, depth + 1)
        check_depth(result)
    except (ValueError, ujson.JSONDecodeError, RecursionError):
        pass


def fuzz_edge_values(data: bytes) -> None:
    """Fuzz edge case values."""
    edge_cases = [
        'null',
        'true',
        'false',
        '0',
        '1',
        '-1',
        '1.0',
        '-1.0',
        '1e10',
        '1E10',
        '-1e-10',
        'null',
        '""',
        '[]',
        '{}',
        '" "',
        '"\\n"',
        '"\\t"',
        '"\\\\"',
        '"\\""',
        '9007199254740992',  # Large integer (2^53 + 1)
        '-9007199254740992',
    ]

    for case in edge_cases:
        try:
            result = ujson.loads(case)
        except (ValueError, ujson.JSONDecodeError):
            pass


def fuzz_large_numbers(data: bytes) -> None:
    """Fuzz handling of large numbers."""
    input_str = safe_unicode_decode(data)

    try:
        # Test with large integers
        large_int = int(input_str) if input_str.lstrip('-').isdigit() else 0
        result = ujson.dumps(large_int)
        _ = ujson.loads(result)
    except (ValueError, OverflowError):
        pass

    try:
        # Test with scientific notation
        result = ujson.dumps(input_str)
    except (TypeError, OverflowError):
        pass


def fuzz_special_floats(data: bytes) -> None:
    """Fuzz special float values."""
    # Note: ujson may not support these, so we catch errors
    try:
        result = ujson.dumps(math.nan)
    except (ValueError, TypeError):
        pass

    try:
        result = ujson.dumps(math.inf)
    except (ValueError, TypeError):
        pass

    try:
        result = ujson.dumps(float('-inf'))
    except (ValueError, TypeError):
        pass


def fuzz_unicode_strings(data: bytes) -> None:
    """Fuzz Unicode handling."""
    try:
        decoded = safe_unicode_decode(data)
        result = ujson.dumps(decoded)
        _ = ujson.loads(result)
    except (ValueError, ujson.JSONDecodeError, TypeError, OverflowError):
        pass


def fuzz_unicode_escapes(data: bytes) -> None:
    """Fuzz Unicode escape sequences."""
    escape_sequences = [
        '"\\u0041"',  # A
        '"\\u00A9"',  # Copyright symbol
        '"\\u2600"',  # Sun
        '"\\uD83D\\uDE00"',  # Emoji
        '"Hello\\nWorld"',
        '"Hello\\tWorld"',
        '"Hello\\"World"',
        '"Hello\\\\World"',
    ]

    for seq in escape_sequences:
        try:
            result = ujson.loads(seq)
        except (ValueError, ujson.JSONDecodeError):
            pass


def fuzz_control_characters(data: bytes) -> None:
    """Fuzz control characters in strings."""
    # Skip null bytes in JSON
    for i in range(1, 32):
        if i == ord('\n') or i == ord('\r') or i == ord('\t'):
            continue
        try:
            test_str = f'"test{chr(i)}value"'
            result = ujson.loads(test_str)
        except (ValueError, ujson.JSONDecodeError):
            pass


def fuzz_truncated_json(data: bytes) -> None:
    """Fuzz truncated JSON input."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    # Try various truncations
    for i in range(1, min(len(input_str), 50)):
        truncated = input_str[:i]
        try:
            result = ujson.loads(truncated)
        except (ValueError, ujson.JSONDecodeError):
            pass


def fuzz_malformed_json(data: bytes) -> None:
    """Fuzz malformed JSON."""
    malformed_samples = [
        '{',
        '[',
        '{"key":}',
        '{"key": "value"',
        '{"key": "value",}',
        '[1, 2,]',
        '{"key": "value" "key2": "value2"}',
        'undefined',
        'NaN',
        'Infinity',
        '+123',
        '01',
        '1.',
        '.1',
        '"',
        "'single quotes'",
    ]

    for sample in malformed_samples:
        try:
            result = ujson.loads(sample)
        except (ValueError, ujson.JSONDecodeError):
            pass


def fuzz_decimal_strings(data: bytes) -> None:
    """Fuzz decimal number parsing."""
    decimal_samples = [
        '3.141592653589793',
        '0.0000001',
        '9999999999999999999',
        '0.12345678901234567890',
        '-0.000001',
        '1e-100',
        '1e100',
        '-1.5e-50',
    ]

    for sample in decimal_samples:
        try:
            result = ujson.loads(sample)
        except (ValueError, ujson.JSONDecodeError):
            pass


def main():
    """Main entry point for fuzzing."""
    # Get input from stdin (LibFuzzer/AFL style) or use provided data
    if len(sys.argv) > 1:
        # Read from file (AFL/LibFuzzer queue)
        with open(sys.argv[1], 'rb') as f:
            data = f.read()
    else:
        # Read from stdin
        data = sys.stdin.buffer.read()

    if not data:
        return

    # Run all fuzz targets
    fuzz_loads_basic(data)
    fuzz_loads_bytes(data)
    fuzz_loads_precise_float(data)
    fuzz_dumps_basic(data)
    fuzz_dumps_params(data)
    fuzz_nested_structures(data)
    fuzz_edge_values(data)
    fuzz_large_numbers(data)
    fuzz_special_floats(data)
    fuzz_unicode_strings(data)
    fuzz_unicode_escapes(data)
    fuzz_control_characters(data)
    fuzz_truncated_json(data)
    fuzz_malformed_json(data)
    fuzz_decimal_strings(data)


if __name__ == '__main__':
    main()
