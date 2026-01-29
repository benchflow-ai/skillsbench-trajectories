#!/usr/bin/env python3
"""LibFuzzer harness for ujson JSON encoder/decoder."""

import sys
import atheris

try:
    import ujson
except ImportError as e:
    print(f"Failed to import ujson: {e}", file=sys.stderr)
    sys.exit(1)


def fuzz_ujson_loads(data: bytes) -> None:
    """Fuzz ujson.loads() JSON parsing."""
    try:
        # Convert bytes to string
        input_str = data.decode('utf-8', errors='ignore')

        # Try to parse JSON
        try:
            ujson.loads(input_str)
        except (ValueError, TypeError, ujson.JSONDecodeError if hasattr(ujson, 'JSONDecodeError') else ValueError):
            pass

    except (UnicodeDecodeError, MemoryError, RuntimeError):
        pass


def fuzz_ujson_dumps(data: bytes) -> None:
    """Fuzz ujson.dumps() JSON encoding."""
    try:
        # Use data to create various Python objects
        input_str = data.decode('utf-8', errors='ignore')

        # Try to encode various objects
        test_objects = [
            input_str,
            input_str[:50],
            data,
            len(data),
            data.hex(),
        ]

        for obj in test_objects:
            try:
                ujson.dumps(obj)
            except (TypeError, ValueError, OverflowError):
                pass

    except Exception:
        pass


def fuzz_ujson_roundtrip(data: bytes) -> None:
    """Fuzz ujson roundtrip (loads -> dumps)."""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Try roundtrip
        try:
            parsed = ujson.loads(input_str)
            ujson.dumps(parsed)
        except (ValueError, TypeError):
            pass

    except Exception:
        pass


def fuzz_ujson_numbers(data: bytes) -> None:
    """Fuzz ujson with various numeric formats."""
    try:
        # Extract numeric sequences from data
        numeric_str = ''.join(c for c in data.decode('utf-8', errors='ignore') if c.isdigit() or c in '.-+eE')

        if numeric_str:
            # Try to parse as JSON number
            try:
                ujson.loads(numeric_str)
            except (ValueError, TypeError):
                pass

            # Try various number formats
            for test_str in [numeric_str, f"[{numeric_str}]", f'{{"{numeric_str}":1}}']:
                try:
                    ujson.loads(test_str)
                except (ValueError, TypeError):
                    pass

    except Exception:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing function."""
    fuzz_ujson_loads(data)
    fuzz_ujson_dumps(data)
    fuzz_ujson_roundtrip(data)
    fuzz_ujson_numbers(data)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
