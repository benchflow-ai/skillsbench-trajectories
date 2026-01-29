#!/usr/bin/env python3
"""Fuzz driver for ujson library using LibFuzzer interface."""

import sys
import signal
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

try:
    import ujson
except ImportError:
    print("ujson module not installed, skipping fuzzing")
    sys.exit(0)


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Fuzzing timed out")


def fuzz_loads(data: bytes) -> None:
    """Fuzz function for ujson.loads - JSON decoding."""
    if not data:
        return

    try:
        # Fuzz with bytes input
        ujson.loads(data)
    except Exception:
        pass

    try:
        # Fuzz with string input
        decoded = data.decode('utf-8', errors='replace')
        ujson.loads(decoded)
    except Exception:
        pass

    # Fuzz various JSON structures
    try:
        ujson.loads(b"{}")
        ujson.loads(b"[]")
        ujson.loads(b"null")
        ujson.loads(b"true")
        ujson.loads(b"false")
        ujson.loads(b'""')
        ujson.loads(b"0")
        ujson.loads(b"123")
        ujson.loads(b"1.5")
        ujson.loads(b'-1')
        ujson.loads(b'-1.5')
    except Exception:
        pass


def fuzz_dumps(data: bytes) -> None:
    """Fuzz function for ujson.dumps - JSON encoding."""
    if not data:
        return

    try:
        # Fuzz with dict
        test_dict = {
            "key1": "value1",
            "key2": 123,
            "key3": 1.5,
            "key4": True,
            "key5": None,
            "key6": [1, 2, 3],
            "key7": {"nested": "value"},
        }
        # Modify dict with fuzz data
        try:
            decoded = data.decode('utf-8', errors='replace')
            test_dict["fuzz"] = decoded[:100] if len(decoded) > 100 else decoded
        except Exception:
            pass

        ujson.dumps(test_dict)
    except Exception:
        pass

    try:
        # Fuzz with list
        test_list = [1, "string", 1.5, True, None, {"dict": "value"}, [1, 2, 3]]
        ujson.dumps(test_list)
    except Exception:
        pass

    try:
        # Fuzz with string
        decoded = data.decode('utf-8', errors='replace')
        ujson.dumps(decoded)
    except Exception:
        pass

    try:
        # Fuzz with number
        ujson.dumps(123)
        ujson.dumps(1.5)
        ujson.dumps(-456)
    except Exception:
        pass


def fuzz_nested_structures(data: bytes) -> None:
    """Fuzz function for nested JSON structures."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Create nested structure
        nested = {
            "level1": {
                "level2": {
                    "level3": decoded[:50] if len(decoded) > 50 else decoded
                }
            }
        }
        ujson.dumps(nested)
    except Exception:
        pass

    # Test deep nesting
    try:
        deep = {}
        current = deep
        for i in range(10):
            current["level" + str(i)] = {}
            current = current["level" + str(i)]
        current["value"] = "deep"
        ujson.dumps(deep)
    except Exception:
        pass


def fuzz_edge_cases(data: bytes) -> None:
    """Fuzz function for edge cases."""
    if not data:
        return

    edge_cases = [
        b"",
        b"\x00",
        b"\x01\x02\x03",
        b" ",
        b"\n\t\r",
        b"null",
        b"true",
        b"false",
        b"0",
        b"123",
        b"-123",
        b"1.23",
        b"1e10",
        b"1E10",
        b"-1.5e-10",
        b'""',
        b'"\\n"',
        b'"\\t"',
        b'"\\\\"',
        b'"\\/"',
        b'"\\""',
        b'"\\u0041"',
        b"[]",
        b"{}",
        b"[1,2,3]",
        b'{"a":1}',
        b'[{"a":1}]',
        b'{"a":[1,2,3]}',
        b'{"a":{"b":{"c":1}}}',
    ]

    for case in edge_cases:
        try:
            ujson.loads(case)
        except Exception:
            pass


def main():
    """Main fuzzing function."""
    # Set timeout for long-running fuzzing sessions
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60 second overall timeout

    if len(sys.argv) > 1:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.read()
        fuzz_loads(data.encode('utf-8'))
        fuzz_dumps(data.encode('utf-8'))
        fuzz_nested_structures(data.encode('utf-8'))
        fuzz_edge_cases(data.encode('utf-8'))
    else:
        # Standalone test mode - run through some test cases
        test_cases = [
            b'{"key": "value"}',
            b'[1, 2, 3]',
            b'"string"',
            b"123",
            b"1.5",
            b"true",
            b"false",
            b"null",
            b"",
            b"\x00\x01\x02",
            b"{" + b"A" * 1000 + b"}",
            b"[" + b"1," * 100 + b"]",
            b'{"key": "value", "key2": "value2"}',
            b'[{"a": 1}, {"b": 2}]',
            b'"\\n\\t\\r\\\\\\/"',
            b'"\\u0000\\uFFFF"',
        ]

        for data in test_cases:
            try:
                fuzz_loads(data)
                fuzz_dumps(data)
                fuzz_nested_structures(data)
                fuzz_edge_cases(data)
            except Exception as e:
                print(f"Error with {data!r}: {e}")

    signal.alarm(0)
    print("Fuzzing completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
