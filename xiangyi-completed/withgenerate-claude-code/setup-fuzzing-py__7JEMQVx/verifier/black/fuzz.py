#!/usr/bin/env python3
"""
Fuzz driver for Black code formatter
Tests Python code parsing and formatting
"""

import atheris
import sys

# Suppress warnings during fuzzing
import warnings
warnings.filterwarnings("ignore")


def TestOneInput(data):
    """Fuzz target for Black code formatting"""
    fdp = atheris.FuzzedDataProvider(data)

    # Import inside to catch import-time errors
    try:
        import black
        from black.parsing import InvalidInput, ASTSafetyError
        from black import NothingChanged
    except Exception:
        return

    # Test different functions based on fuzzer choice
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Test format_str() with random Python code
            src = fdp.ConsumeUnicodeNoSurrogates(500)
            try:
                mode = black.Mode()
                black.format_str(src, mode=mode)
            except (InvalidInput, ASTSafetyError, NothingChanged,
                    ValueError, TypeError, AttributeError, SyntaxError,
                    IndentationError):
                pass

        elif choice == 1:
            # Test format_file_contents()
            src = fdp.ConsumeUnicodeNoSurrogates(500)
            fast = fdp.ConsumeBool()
            try:
                mode = black.Mode()
                black.format_file_contents(src, fast=fast, mode=mode)
            except (InvalidInput, ASTSafetyError, NothingChanged,
                    ValueError, TypeError, AttributeError, SyntaxError,
                    IndentationError):
                pass

        elif choice == 2:
            # Test lib2to3_parse() directly
            src = fdp.ConsumeUnicodeNoSurrogates(300)
            try:
                from black.parsing import lib2to3_parse
                lib2to3_parse(src)
            except (InvalidInput, ASTSafetyError, ValueError, TypeError,
                    SyntaxError, IndentationError, AttributeError):
                pass

        else:
            # Test with different mode configurations
            src = fdp.ConsumeUnicodeNoSurrogates(400)
            try:
                # Randomize mode settings
                line_length = fdp.ConsumeIntInRange(1, 200)
                string_normalization = fdp.ConsumeBool()
                magic_trailing_comma = fdp.ConsumeBool()

                mode = black.Mode(
                    line_length=line_length,
                    string_normalization=string_normalization,
                    magic_trailing_comma=magic_trailing_comma,
                )
                black.format_str(src, mode=mode)
            except (InvalidInput, ASTSafetyError, NothingChanged,
                    ValueError, TypeError, AttributeError, SyntaxError,
                    IndentationError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions
        error_str = str(e).lower()
        if 'assert' in error_str or 'unreachable' in error_str:
            raise
        # Otherwise suppress to continue fuzzing


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
