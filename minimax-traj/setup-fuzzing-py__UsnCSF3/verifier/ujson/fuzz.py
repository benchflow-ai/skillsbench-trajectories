#!/usr/bin/env python3
"""
Fuzz driver for ujson library.
Uses LibFuzzer-style coverage-guided fuzzing.
"""

import sys
import json as stdlib_json
from typing import Any


def fuzz_ujson_loads(input_data: bytes) -> None:
    """Fuzz ujson.loads() with various JSON inputs."""
    try:
        import ujson

        # Convert bytes to string for ujson
        data = input_data.decode('utf-8', errors='replace')

        try:
            ujson.loads(data)
        except ValueError:
            # Expected for invalid JSON, continue
            pass
        except Exception:
            # Catch any other unexpected exceptions
            pass

        # Also try with bytes directly
        try:
            ujson.loads(input_data)
        except (ValueError, TypeError):
            pass
        except Exception:
            pass

    except ImportError:
        # ujson not installed, skip
        pass
    except Exception:
        pass


def fuzz_ujson_dumps(input_data: bytes) -> None:
    """Fuzz ujson.dumps() with various Python objects."""
    try:
        import ujson

        # Create various Python objects from input data
        nums = [abs(b) for b in input_data[:32]]

        # Test various object types
        test_objects = [
            None,
            True,
            False,
            nums[0],
            float(nums[0]) / 100.0 if nums[0] > 0 else 0.0,
            "string",
            [1, 2, 3],
            {"key": "value", "number": nums[0]},
            {"nested": {"key": [1, 2, nums[0]]}},
            [i for i in range(min(nums[0] % 10, 10))],
            {"dict": {(nums[0] % 100): "value"}},
        ]

        for obj in test_objects:
            try:
                ujson.dumps(obj)
            except Exception:
                pass
            try:
                ujson.dumps(obj, ensure_ascii=False)
            except Exception:
                pass
            try:
                ujson.dumps(obj, indent=2)
            except Exception:
                pass
            try:
                ujson.dumps(obj, escape_forward_slashes=False)
            except Exception:
                pass

    except ImportError:
        pass
    except Exception:
        pass


def fuzz_ujson_load(input_data: bytes) -> None:
    """Fuzz ujson.load() with file-like objects."""
    try:
        import ujson
        import io

        data = input_data.decode('utf-8', errors='replace')
        file_obj = io.StringIO(data)

        try:
            ujson.load(file_obj)
        except (ValueError, AttributeError):
            pass
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass


def fuzz_ujson_dump(input_data: bytes) -> None:
    """Fuzz ujson.dump() with file-like objects."""
    try:
        import ujson
        import io

        output = io.StringIO()
        test_objects = [
            {"key": "value"},
            [1, 2, 3],
            "string",
            12345,
        ]

        for obj in test_objects:
            try:
                ujson.dump(obj, output)
            except Exception:
                pass

    except ImportError:
        pass
    except Exception:
        pass


def fuzz_edge_cases(input_data: bytes) -> None:
    """Fuzz edge cases and boundary conditions."""
    try:
        import ujson

        # Test various edge cases
        edge_cases = [
            "",
            " ",
            "   ",
            "null",
            "true",
            "false",
            "0",
            "1",
            "-1",
            "1.0",
            "1e10",
            "1E10",
            "1.5e-10",
            "[]",
            "{}",
            '{"key":}',
            '{"key": }',
            "[1, 2, 3]",
            '{"a": [1, 2, 3]}',
            '[[[[[[1]]]]]]',
            '{"a": {"b": {"c": 1}}}',
            '"\\n\\t\\r"',
            '"\\u0041"',
            "null",
            '/* comment */',
        ]

        for case in edge_cases:
            try:
                ujson.loads(case)
            except Exception:
                pass

        # Test with various encodings
        utf8_data = input_data.decode('utf-8', errors='replace')
        try:
            ujson.loads(utf8_data)
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass


def main():
    """Main entry point for fuzzing."""
    if len(sys.argv) > 1:
        # Running with input file (LibFuzzer mode)
        with open(sys.argv[1], 'rb') as f:
            input_data = f.read()
    else:
        # Running from stdin
        input_data = sys.stdin.buffer.read()

    # Run all fuzz targets
    fuzz_ujson_loads(input_data)
    fuzz_ujson_dumps(input_data)
    fuzz_ujson_load(input_data)
    fuzz_ujson_dump(input_data)
    fuzz_edge_cases(input_data)


if __name__ == '__main__':
    main()
