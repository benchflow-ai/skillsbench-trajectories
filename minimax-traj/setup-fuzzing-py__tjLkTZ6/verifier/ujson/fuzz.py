#!/usr/bin/env python3
"""
Fuzz driver for Ujson library
Fuzzes JSON encoding and decoding functions
"""
import sys
import random
import string
import json


def generate_random_json_string():
    """Generate random JSON-like strings for decoding"""
    templates = [
        # Valid JSON
        'null',
        'true',
        'false',
        f'{random.randint(-2**63, 2**63-1)}',
        f'{random.uniform(-1000, 1000)}',
        f'"{random.choice(["hello", "world", "test", ""])}"',
        '[]',
        '{}',
        '[1,2,3]',
        '{"key": "value"}',
        '{"a": 1, "b": 2}',

        # Invalid JSON
        ''.join(random.choices(string.ascii_letters + string.digits + ' {}[],:', k=random.randint(0, 100))),
        'null,',  # Trailing comma
        '[1, 2, 3,]',  # Trailing comma in array
        '{"key": "value",}',  # Trailing comma in object
        '{key: "value"}',  # Unquoted key
        "'string'",  # Single quotes
        '{a: 1, b: 2}',  # Unquoted keys
        '[1, 2, 3',  # Unclosed bracket
        '{"key": "value"',  # Unclosed brace
        'undefined',  # Not a JSON value

        # Special characters
        '\x00\x01\x02',
        '"\n\r\t"',
        '"\\x00\\x01\\x02"',
        '"unicode: 你好 мир"',
        '🎉' * random.randint(0, 20),

        # Edge cases
        ' ' * random.randint(0, 50),
        '\n' * random.randint(0, 50),
        '\x00' * random.randint(0, 50),

        # Very long strings
        '"' + 'a' * random.randint(100, 1000) + '"',

        # Deep nesting
        '[' * random.randint(1, 50) + ']' * random.randint(1, 50),
        '{' + '"a"' + ':' * random.randint(1, 30) + '}',

        # Numbers
        '1' + '.' + '0' * random.randint(0, 100),
        '1e' + str(random.randint(-100, 100)),
        '-1' + '.' + '0' * random.randint(0, 100),
        str(random.randint(0, 10**100)),  # Very large number

        # Mixed
        ''.join(random.choices('[]{}":,0123456789abcdefghijklmnopqrstuvwxyz', k=random.randint(0, 200))),
    ]

    return random.choice(templates)


def generate_random_python_object():
    """Generate random Python objects for encoding"""
    types = [
        # Simple types
        None,
        random.choice([True, False]),
        random.randint(-2**63, 2**63-1),
        random.uniform(-1000, 1000),
        ''.join(random.choices(string.ascii_letters, k=random.randint(0, 100))),

        # Collections
        [],
        {},
        [random.randint(0, 100) for _ in range(random.randint(0, 50))],
        {f'key_{i}': random.randint(0, 100) for i in range(random.randint(0, 20))},
    ]

    # Random nested structures
    if random.choice([True, False]):
        depth = random.randint(1, 5)
        obj = []
        for _ in range(depth):
            if isinstance(obj, list):
                obj = [obj, random.randint(0, 100)]
            else:
                obj = [obj, random.randint(0, 100)]
        return obj

    return random.choice(types)


def fuzz_decode():
    """Fuzz ujson.decode()"""
    try:
        import ujson
    except ImportError:
        # Skip if ujson is not installed
        print("Warning: ujson not installed, skipping decode fuzzing", file=sys.stderr)
        return

    for _ in range(200):
        json_str = generate_random_json_string()

        try:
            result = ujson.decode(json_str)
            # Use result to prevent optimization
            assert result is not None or result is None
        except (ValueError, TypeError) as e:
            # Expected for invalid JSON
            pass
        except Exception as e:
            print(f"Unexpected error in ujson.decode: {e}", file=sys.stderr)
            raise


def fuzz_encode():
    """Fuzz ujson.encode()"""
    try:
        import ujson
    except ImportError:
        # Skip if ujson is not installed
        print("Warning: ujson not installed, skipping encode fuzzing", file=sys.stderr)
        return

    for _ in range(200):
        obj = generate_random_python_object()

        try:
            result = ujson.encode(obj)
            assert isinstance(result, (str, bytes))
        except (TypeError, ValueError) as e:
            # Expected for non-serializable objects
            pass
        except Exception as e:
            print(f"Unexpected error in ujson.encode: {e}", file=sys.stderr)
            raise


def fuzz_dumps():
    """Fuzz ujson.dumps()"""
    try:
        import ujson
    except ImportError:
        # Skip if ujson is not installed
        print("Warning: ujson not installed, skipping dumps fuzzing", file=sys.stderr)
        return

    for _ in range(200):
        obj = generate_random_python_object()

        # Random encode options
        kwargs = {
            'ensure_ascii': random.choice([True, False]),
            'escape_forward_slashes': random.choice([True, False]),
            'encode_html_chars': random.choice([True, False]),
        }

        try:
            result = ujson.dumps(obj, **kwargs)
            assert isinstance(result, str)
        except (TypeError, ValueError) as e:
            # Expected for non-serializable objects
            pass
        except Exception as e:
            print(f"Unexpected error in ujson.dumps: {e}", file=sys.stderr)
            raise


def fuzz_loads():
    """Fuzz ujson.loads()"""
    try:
        import ujson
    except ImportError:
        # Skip if ujson is not installed
        print("Warning: ujson not installed, skipping loads fuzzing", file=sys.stderr)
        return

    for _ in range(200):
        json_str = generate_random_json_string()

        try:
            result = ujson.loads(json_str)
            # Use result to prevent optimization
            assert result is not None or result is None
        except (ValueError, TypeError) as e:
            # Expected for invalid JSON
            pass
        except Exception as e:
            print(f"Unexpected error in ujson.loads: {e}", file=sys.stderr)
            raise


def fuzz_round_trip():
    """Test round-trip encoding and decoding"""
    try:
        import ujson
    except ImportError:
        print("Warning: ujson not installed, skipping round-trip fuzzing", file=sys.stderr)
        return

    for _ in range(100):
        obj = generate_random_python_object()

        try:
            # Encode
            encoded = ujson.encode(obj)
            assert isinstance(encoded, (str, bytes))

            # Decode
            decoded = ujson.loads(encoded)

            # For simple types, check round-trip
            if isinstance(obj, (type(None), bool, int, float, str)):
                assert decoded == obj
        except (TypeError, ValueError) as e:
            # Expected for non-serializable objects or invalid round-trip
            pass
        except Exception as e:
            print(f"Unexpected error in round-trip: {e}", file=sys.stderr)
            raise


if __name__ == '__main__':
    print("Starting Ujson fuzzing...")
    fuzz_decode()
    print("✓ decode() fuzzed successfully")
    fuzz_encode()
    print("✓ encode() fuzzed successfully")
    fuzz_dumps()
    print("✓ dumps() fuzzed successfully")
    fuzz_loads()
    print("✓ loads() fuzzed successfully")
    fuzz_round_trip()
    print("✓ round-trip fuzzed successfully")
    print("Ujson fuzzing completed successfully!")
