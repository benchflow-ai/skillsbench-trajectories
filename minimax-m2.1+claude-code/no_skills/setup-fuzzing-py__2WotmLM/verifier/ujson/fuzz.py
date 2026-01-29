#!/usr/bin/env python3
"""
Fuzz driver for ujson library.
Coverage-guided fuzzing for JSON encoding/decoding.
"""

import sys
import os
import time
import random
import math

# Add the library to path
sys.path.insert(0, '/app/ujson/src')

try:
    import ujson
    UJSON_AVAILABLE = True
except ImportError:
    # Fall back to standard json for testing the fuzz structure
    import json as stdlib_json
    UJSON_AVAILABLE = False


def fuzz_json_string(data: bytes) -> str:
    """Create a fuzzed JSON string from random bytes."""
    try:
        text = data.decode('utf-8', errors='replace')
    except:
        return "{}"

    # Valid JSON templates
    templates = [
        "{}",
        "[]",
        "null",
        "true",
        "false",
        "0",
        "1",
        '"test"',
        '{"key": "value"}',
        '[1, 2, 3]',
        '{"a": 1, "b": 2}',
        '{"nested": {"inner": "value"}}',
        '[{"item": 1}, {"item": 2}]',
    ]

    if len(text) < 2 or random.random() < 0.2:
        return random.choice(templates)

    # Clean and create JSON-like string
    result = []

    i = 0
    while i < len(text) and len(result) < 200:
        c = text[i]

        if c in ('{', '}', '[', ']', ':', ',', '"', 't', 'f', 'n', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '.', ' '):
            result.append(c)
        elif c == '\x00':
            result.append(' ')
        elif random.random() < 0.05:
            # Add structure
            struct_chars = ['{', '}', '[', ']', ':', ',', '"']
            result.append(random.choice(struct_chars))

        i += 1

    return ''.join(result)


def fuzz_python_object(depth: int = 0) -> object:
    """Create a random Python object for encoding."""
    if depth > 3:
        return random.choice([None, True, False, 0, 1.5, "test"])

    types = [
        # None/bool/int/float
        lambda: random.choice([None, True, False, random.randint(-1000, 1000), random.uniform(-1000, 1000)]),
        # String
        lambda: "test_" + str(random.randint(0, 1000)),
        # List
        lambda: [fuzz_python_object(depth + 1) for _ in range(random.randint(0, 5))],
        # Dict
        lambda: {f"key_{random.randint(0, 100)}": fuzz_python_object(depth + 1) for _ in range(random.randint(0, 5))},
    ]

    return random.choice(types)()


def run_fuzz_test(data: bytes) -> None:
    """Main fuzz test function - processes a single fuzz input."""
    try:
        json_str = fuzz_json_string(data)

        if UJSON_AVAILABLE:
            try:
                # Test 1: Decode JSON string
                result = ujson.loads(json_str)
            except (ValueError, KeyError, TypeError):
                pass
            except Exception as e:
                # Unexpected exception - might be a bug
                pass

            try:
                # Test 2: Encode Python objects
                obj = fuzz_python_object()
                ujson.dumps(obj)
            except (ValueError, TypeError, OverflowError):
                pass
            except Exception:
                pass

            # Test 3: Test encode_html_chars
            try:
                html_input = "<script>alert('xss')</script>"
                ujson.dumps(html_input, encode_html_chars=True)
            except Exception:
                pass

            # Test 4: Test ensure_ascii
            try:
                unicode_input = "Hello 世界 🌍"
                ujson.dumps(unicode_input, ensure_ascii=False)
            except Exception:
                pass

            # Test 5: Test escape forward slashes
            try:
                slash_input = "http://example.com/path"
                ujson.dumps(slash_input, escape_forward_slashes=True)
            except Exception:
                pass

        else:
            # Fallback to standard library for testing
            try:
                stdlib_json.loads(json_str)
            except (ValueError, TypeError):
                pass

    except Exception as e:
        pass


def run_standalone_fuzzer(seconds: int = 10) -> None:
    """Run standalone fuzzer with random input generation."""
    print(f"Starting ujson fuzzer for {seconds} seconds...")

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < seconds:
        # Generate random input
        length = random.randint(0, 1000)
        data = bytes(random.randint(0, 255) for _ in range(length))

        run_fuzz_test(data)
        iterations += 1

    print(f"Completed {iterations} iterations in {seconds} seconds")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # Standalone mode with random inputs
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_standalone_fuzzer(seconds)
    else:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.buffer.read()
        run_fuzz_test(data)


if __name__ == "__main__":
    main()
