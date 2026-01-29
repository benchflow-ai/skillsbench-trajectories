"""
LibFuzzer-style fuzz driver for ujson library.
This fuzzer tests ujson.dumps() and ujson.loads() with various inputs.
"""

import sys
import atheris

import ujson


def fuzz_ujson(input_bytes):
    """Fuzz ujson.loads() and ujson.dumps() with various inputs."""
    fdp = atheris.FuzzedDataProvider(input_bytes)

    try:
        # Get a random string from the input
        input_str = fdp.consume_string(fdp.remaining_bytes())

        # Test ujson.loads() with various JSON-like strings
        try:
            result = ujson.loads(input_str)
        except (ValueError, ujson.JSONDecodeError, TypeError, KeyError):
            # Expected for invalid JSON
            pass

        # Test ujson.dumps() with various Python objects
        test_objects = [
            input_str,
            input_str.encode('utf-8') if len(input_str) > 0 else b'',
            list(input_str),
            {input_str: input_str} if len(input_str) > 0 else {},
            tuple(input_str[i:i+3] for i in range(0, len(input_str), 3)) if len(input_str) > 0 else (),
        ]

        for obj in test_objects:
            try:
                json_str = ujson.dumps(obj)
                # Try to parse it back
                ujson.loads(json_str)
            except (ValueError, TypeError, KeyError, ujson.JSONDecodeError, OverflowError):
                pass

        # Test with ensure_ascii option
        try:
            ujson.dumps(input_str, ensure_ascii=fdp.consume_bool())
        except (ValueError, TypeError):
            pass

        # Test with indent option
        try:
            indent_val = fdp.consume_int_in_range(0, 10)
            ujson.dumps(input_str, indent=indent_val)
        except (ValueError, TypeError):
            pass

    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, fuzz_ujson)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
