#!/usr/bin/env python3
"""
Fuzz driver for Black Python code formatter.

Target: lib2to3_parse() and format_str()
These parse and format arbitrary Python source code.
"""

import sys
import atheris

# Import black modules with instrumentation
with atheris.instrument_imports():
    from black.parsing import lib2to3_parse, InvalidInput
    from black import format_str, Mode


def TestOneInput(data):
    """
    Fuzz target for Black Python code formatter.

    This fuzzer tests:
    1. lib2to3_parse() - Core Python source parser
    2. format_str() - Main formatting API

    Expected behavior:
    - Valid Python should parse and format successfully
    - Invalid Python should raise InvalidInput
    - No crashes or hangs
    """
    if len(data) == 0:
        return

    # Decode to string
    try:
        source_code = data.decode('utf-8', errors='ignore')
    except Exception:
        return

    # Skip empty or extremely large inputs
    if not source_code or len(source_code) > 50000:
        return

    # Test 1: Fuzz lib2to3_parse() - the core parsing function
    try:
        lib2to3_parse(source_code)
    except InvalidInput:
        # Expected for invalid Python syntax
        pass
    except (SyntaxError, ValueError):
        # Some edge cases
        pass
    except RecursionError:
        # Deep nesting can cause recursion errors
        pass
    except Exception as e:
        # Any other exception is suspicious
        raise

    # Test 2: Fuzz format_str() - the main API
    # Only test if input is not too large (formatting is slower)
    if len(source_code) <= 10000:
        try:
            mode = Mode()
            formatted = format_str(source_code, mode=mode)

            # Optional: Check idempotence
            # formatted_twice = format_str(formatted, mode=mode)
            # assert formatted == formatted_twice

        except InvalidInput:
            # Expected for invalid Python
            pass
        except (ValueError, SyntaxError):
            # Edge cases
            pass
        except RecursionError:
            # Deep nesting
            pass
        except Exception as e:
            # Suspicious exceptions
            raise


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
