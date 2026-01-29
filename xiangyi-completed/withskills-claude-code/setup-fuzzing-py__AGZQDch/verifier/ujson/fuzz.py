#!/usr/bin/env python3
"""
Fuzz driver for ujson (UltraJSON) library.

Target: ujson.loads() - C-based JSON decoder
CRITICAL: This is a native extension with known security history.

This fuzzer should be run with Address Sanitizer (ASAN) for best results:
    CC="clang -fsanitize=address" pip install --no-binary ujson ujson
"""

import sys
import atheris

# Note: ujson is a C extension, so instrument_imports won't add Python coverage.
# However, atheris will still detect crashes in the C code.
with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    """
    Fuzz target for ujson.loads().

    This is a CRITICAL security boundary - ujson is implemented in C
    and has a history of buffer overflow vulnerabilities.

    Expected behavior:
    - Valid JSON should parse successfully
    - Invalid JSON should raise ValueError
    - NO crashes, buffer overflows, or memory corruption

    Run with ASAN to detect memory safety issues.
    """
    # Test ujson.loads() with raw bytes
    try:
        result = ujson.loads(data)

        # Optional: Test round-trip if parse succeeded
        # try:
        #     encoded = ujson.dumps(result)
        #     # Could re-parse to check consistency
        #     ujson.loads(encoded)
        # except Exception:
        #     # dumps might fail for some edge cases (e.g., circular refs)
        #     pass

    except ValueError:
        # Expected for invalid JSON
        pass
    except OverflowError:
        # Extreme numeric values
        pass
    except RecursionError:
        # Deeply nested structures
        pass
    except Exception as e:
        # Any other exception is suspicious
        raise


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
