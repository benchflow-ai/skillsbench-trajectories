#!/usr/bin/env python3
"""
LibFuzzer-style fuzz driver for Black library using Atheris.
Tests Python code formatting and parsing functions.
"""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion
    from black.parsing import lib2to3_parse, parse_ast, InvalidInput


def TestOneInput(data):
    """Fuzz target for Black library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Skip empty inputs
    if len(data) < 1:
        return

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    # Create a basic Mode configuration
    mode = Mode(
        target_versions={TargetVersion.PY38},
        line_length=fdp.ConsumeIntInRange(10, 200),
        string_normalization=fdp.ConsumeBool(),
    )

    try:
        if choice == 0:
            # Fuzz format_str with Python code
            code = fdp.ConsumeUnicodeNoSurrogates(500)
            if code:
                try:
                    black.format_str(code, mode=mode)
                except (InvalidInput, ValueError, TypeError, black.parsing.InvalidInput):
                    pass

        elif choice == 1:
            # Fuzz lib2to3_parse
            code = fdp.ConsumeUnicodeNoSurrogates(500)
            if code:
                try:
                    lib2to3_parse(code)
                except (InvalidInput, ValueError, SyntaxError):
                    pass

        elif choice == 2:
            # Fuzz parse_ast
            code = fdp.ConsumeUnicodeNoSurrogates(500)
            if code:
                try:
                    parse_ast(code)
                except (ValueError, SyntaxError):
                    pass

        elif choice == 3:
            # Fuzz format_str with different mode options
            code = fdp.ConsumeUnicodeNoSurrogates(500)
            if code:
                try:
                    # Try with different string normalization
                    alt_mode = Mode(
                        target_versions={TargetVersion.PY38},
                        line_length=fdp.ConsumeIntInRange(10, 200),
                        string_normalization=not mode.string_normalization,
                    )
                    black.format_str(code, mode=alt_mode)
                except (InvalidInput, ValueError, TypeError, black.parsing.InvalidInput):
                    pass

        elif choice == 4:
            # Fuzz assert_equivalent with two code snippets
            code1 = fdp.ConsumeUnicodeNoSurrogates(250)
            code2 = fdp.ConsumeUnicodeNoSurrogates(250)
            if code1 and code2:
                try:
                    black.assert_equivalent(code1, code2)
                except (ValueError, SyntaxError, AssertionError, black.parsing.InvalidInput):
                    pass

    except Exception as e:
        # Allow expected exceptions but catch unexpected crashes
        if not isinstance(e, (ValueError, TypeError, SyntaxError, AssertionError,
                            InvalidInput, KeyError, AttributeError, RecursionError)):
            raise


def main():
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
