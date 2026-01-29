#!/usr/bin/env python3
"""
Fuzz driver for Black Python code formatter.
Targets the parsing and formatting functions with various Python source code inputs.
"""

import sys
import atheris

with atheris.instrument_imports():
    from black import parsing, mode
    from black.parsing import lib2to3_parse, parse_ast, InvalidInput


def TestOneInput(data):
    """Fuzz entry point for Black parser functions."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 1)

    try:
        if choice == 0:
            # Fuzz lib2to3_parse()
            src_txt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))

            # Generate random target versions
            target_versions = set()
            if fdp.ConsumeBool():
                from black.mode import TargetVersion
                available_versions = list(TargetVersion)
                num_versions = fdp.ConsumeIntInRange(0, len(available_versions))
                for _ in range(num_versions):
                    if available_versions:
                        target_versions.add(fdp.PickValueInList(available_versions))

            try:
                result = lib2to3_parse(src_txt, target_versions=target_versions)
            except (InvalidInput, SyntaxError, ValueError, IndexError, KeyError, RecursionError):
                pass  # Expected exceptions

        elif choice == 1:
            # Fuzz parse_ast()
            src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))

            try:
                result = parse_ast(src)
            except (SyntaxError, ValueError, RecursionError, MemoryError):
                pass  # Expected exceptions

    except Exception as e:
        # Catch any unexpected exceptions
        exception_type = type(e).__name__
        safe_exceptions = [
            'InvalidInput', 'SyntaxError', 'ValueError', 'IndexError', 'KeyError',
            'RecursionError', 'MemoryError', 'AttributeError', 'TypeError',
            'OverflowError', 'UnicodeDecodeError'
        ]
        if exception_type not in safe_exceptions:
            raise  # Re-raise unexpected exceptions


def main():
    """Main entry point for fuzzing."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
