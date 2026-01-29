#!/usr/bin/env python3
"""Fuzz driver for black library - Python code formatting."""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion
    from black.parsing import InvalidInput, ASTSafetyError
    from black.report import NothingChanged


def TestOneInput(data: bytes) -> None:
    """Main fuzz target function for black library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Format arbitrary Python code strings
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 2000)
        )
        mode = Mode()
        black.format_str(code, mode=mode)
    except (
        InvalidInput,
        SyntaxError,
        ValueError,
        TypeError,
        NothingChanged,
        ASTSafetyError,
        AssertionError,
        RecursionError,
        IndentationError,
        TabError,
        UnicodeDecodeError,
        KeyError,
    ):
        pass

    # Test 2: Format with different line lengths
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 1000)
        )
        line_length = fdp.ConsumeIntInRange(1, 200)
        mode = Mode(line_length=line_length)
        black.format_str(code, mode=mode)
    except (
        InvalidInput,
        SyntaxError,
        ValueError,
        TypeError,
        NothingChanged,
        ASTSafetyError,
        AssertionError,
        RecursionError,
        IndentationError,
        TabError,
        UnicodeDecodeError,
        KeyError,
    ):
        pass

    # Test 3: Format with pyi mode
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 1000)
        )
        mode = Mode(is_pyi=True)
        black.format_str(code, mode=mode)
    except (
        InvalidInput,
        SyntaxError,
        ValueError,
        TypeError,
        NothingChanged,
        ASTSafetyError,
        AssertionError,
        RecursionError,
        IndentationError,
        TabError,
        UnicodeDecodeError,
        KeyError,
    ):
        pass

    # Test 4: Format with string normalization disabled
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 1000)
        )
        mode = Mode(string_normalization=False)
        black.format_str(code, mode=mode)
    except (
        InvalidInput,
        SyntaxError,
        ValueError,
        TypeError,
        NothingChanged,
        ASTSafetyError,
        AssertionError,
        RecursionError,
        IndentationError,
        TabError,
        UnicodeDecodeError,
    ):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
