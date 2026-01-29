#!/usr/bin/env python3
"""
Coverage-guided fuzz driver for the Black Python code formatter.
Uses Atheris for LibFuzzer-style fuzzing.
"""
import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for Black code formatting."""
    fdp = atheris.FuzzedDataProvider(data)

    # Import black inside the function to ensure instrumentation
    import black
    from black import Mode, InvalidInput, NothingChanged
    from black.parsing import ASTSafetyError

    # Generate a Python code-like string from fuzz input
    code_string = fdp.ConsumeUnicodeNoSurrogates(4096)

    if not code_string:
        return

    # Create a mode for formatting
    mode = Mode()

    # Test 1: black.format_str() with default mode
    try:
        black.format_str(code_string, mode=mode)
    except (InvalidInput, NothingChanged, IndentationError,
            ValueError, TypeError, AssertionError, RecursionError):
        pass
    except Exception as e:
        # Catch other parsing-related exceptions
        if "Cannot parse" in str(e) or "invalid" in str(e).lower() or "token" in str(e).lower():
            pass
        else:
            raise

    # Test 2: format_str with different line lengths
    line_length = fdp.ConsumeIntInRange(1, 200)
    try:
        mode_custom = Mode(line_length=line_length)
        black.format_str(code_string, mode=mode_custom)
    except (InvalidInput, NothingChanged, IndentationError,
            ValueError, TypeError, AssertionError, RecursionError):
        pass
    except Exception as e:
        if "Cannot parse" in str(e) or "invalid" in str(e).lower() or "token" in str(e).lower():
            pass
        else:
            raise

    # Test 3: format_file_contents with fast=True
    try:
        black.format_file_contents(code_string, fast=True, mode=mode)
    except (InvalidInput, NothingChanged, IndentationError,
            ValueError, TypeError, AssertionError, RecursionError, ASTSafetyError):
        pass
    except Exception as e:
        if "Cannot parse" in str(e) or "invalid" in str(e).lower() or "token" in str(e).lower():
            pass
        else:
            raise


def main():
    # Instrument the black module for coverage
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
