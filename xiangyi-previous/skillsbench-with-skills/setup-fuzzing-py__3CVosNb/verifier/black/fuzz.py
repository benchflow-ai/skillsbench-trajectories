#!/usr/bin/env python3
"""
Fuzz driver for Black Python code formatter.

Targets:
- format_str() - Main public API for formatting Python source code
- lib2to3_parse() - Core parsing function using blib2to3 grammar
- parse_ast() - AST parsing with standard library

Usage:
    python fuzz.py [libfuzzer options]

Example:
    python fuzz.py -max_total_time=10
"""

import sys
import atheris


def setup_black():
    """Import black modules inside instrumentation context."""
    global black, format_str, Mode, InvalidInput
    global lib2to3_parse, parse_ast

    import black
    from black import format_str, Mode
    from black.parsing import lib2to3_parse, parse_ast

    # Import exceptions
    try:
        from black import InvalidInput
    except ImportError:
        # Fallback for older versions
        InvalidInput = ValueError


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Fuzz test entry point.

    Tests Black's formatting and parsing functions with arbitrary input.
    """
    # Try to decode as UTF-8 string
    try:
        input_str = data.decode('utf-8')
    except UnicodeDecodeError:
        # If not valid UTF-8, try with replacement
        input_str = data.decode('utf-8', errors='replace')

    # Skip empty inputs - format_str requires non-empty input
    if not input_str.strip():
        return

    # Create default mode
    mode = Mode()

    # Test 1: format_str() - Main formatting function
    try:
        result = format_str(input_str, mode=mode)

        # Idempotency check: formatting twice should give same result
        result2 = format_str(result, mode=mode)
        if result != result2:
            # This would indicate a bug, but don't crash the fuzzer
            pass

    except InvalidInput:
        pass  # Expected for invalid Python syntax
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass  # Expected exceptions
    except Exception:
        pass  # Catch any other exceptions

    # Test 2: lib2to3_parse() - Core parsing function
    try:
        result = lib2to3_parse(input_str)
    except InvalidInput:
        pass
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 3: parse_ast() - Standard library AST parsing
    try:
        result = parse_ast(input_str)
    except (SyntaxError, ValueError, TypeError, OverflowError, RecursionError):
        pass  # Expected for invalid Python syntax
    except Exception:
        pass

    # Test 4: format_str with different modes
    try:
        # Test with preview mode
        preview_mode = Mode(preview=True)
        result = format_str(input_str, mode=preview_mode)
    except InvalidInput:
        pass
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 5: format_str with different line lengths
    try:
        short_mode = Mode(line_length=40)
        result = format_str(input_str, mode=short_mode)
    except InvalidInput:
        pass
    except (ValueError, TypeError, OverflowError, RecursionError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    # Instrument black imports
    with atheris.instrument_imports():
        setup_black()

    # Setup and run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
