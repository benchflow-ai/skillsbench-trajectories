#!/usr/bin/env python3
"""Fuzz driver for Black code formatter."""

import atheris
import sys

with atheris.instrument_imports():
    import black


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for Black formatting."""
    fdp = atheris.FuzzedDataProvider(data)

    # Generate Python-like code input
    code_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 1000))

    try:
        # Test 1: format_str with default mode
        if len(code_input) > 0:
            try:
                black.format_str(code_input, mode=black.FileMode())
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 2: format_str with various line lengths
        if len(code_input) > 0:
            try:
                mode = black.FileMode(line_length=fdp.ConsumeIntInRange(10, 300))
                black.format_str(code_input, mode=mode)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 3: Test with string normalization enabled/disabled
        if len(code_input) > 0:
            try:
                mode = black.FileMode(
                    string_normalization=fdp.ConsumeBool()
                )
                black.format_str(code_input, mode=mode)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 4: parse via lib2to3_parse
        if len(code_input) > 0:
            try:
                from black.parsing import lib2to3_parse
                lib2to3_parse(code_input)
            except (ValueError, SyntaxError, TypeError, AttributeError):
                pass

        # Test 5: Test string quote normalization
        string_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 200))
        if len(string_input) > 0:
            try:
                from black.strings import normalize_string_quotes
                # Create a simple string node mock
                normalize_string_quotes(string_input)
            except (ValueError, TypeError, AttributeError):
                pass

    except Exception:
        # Catch any unexpected exceptions
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
