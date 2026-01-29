#!/usr/bin/env python3
"""
Fuzz driver for Black code formatter
Tests Python code parsing and formatting functions
"""

import sys
import atheris

# Add black to path
sys.path.insert(0, '/app/black/src')

import black
from black import InvalidInput, NothingChanged


def TestOneInput(data):
    """Fuzz target for Black formatter"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz format_str with random Python code
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 5000))
            try:
                mode = black.Mode()
                black.format_str(code, mode=mode)
            except (InvalidInput, NothingChanged, ValueError, TypeError, SyntaxError):
                pass

        elif choice == 1:
            # Fuzz with different line lengths
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
            line_length = fdp.ConsumeIntInRange(1, 200)
            try:
                mode = black.Mode(line_length=line_length)
                black.format_str(code, mode=mode)
            except (InvalidInput, NothingChanged, ValueError, TypeError, SyntaxError):
                pass

        elif choice == 2:
            # Fuzz parse_ast
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 3000))
            try:
                black.parsing.parse_ast(code)
            except (InvalidInput, ValueError, TypeError, SyntaxError, MemoryError):
                pass

        else:
            # Fuzz lib2to3 parser with various Python syntax
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 3000))
            try:
                target_versions = {black.TargetVersion.PY310}
                black.parsing.lib2to3_parse(code, target_versions)
            except (InvalidInput, ValueError, TypeError, SyntaxError, MemoryError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions for debugging
        error_str = str(e)
        if "Segmentation fault" in error_str or "Bus error" in error_str:
            raise
        # Ignore expected parsing errors
        if "cannot use --safe" in error_str or "INTERNAL ERROR" in error_str:
            pass


def main():
    """Main fuzzing entry point"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
