#!/usr/bin/env python3
"""
Fuzz driver for Black library - Python code formatter
Uses Atheris (LibFuzzer-based) for coverage-guided fuzzing
"""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Black library"""
    fdp = atheris.FuzzedDataProvider(data)

    # Generate Python source code
    source_code = fdp.ConsumeUnicodeNoSurrogates(1000)

    if not source_code:
        return

    try:
        # Try to format the code
        # Use different modes for variety
        choice = fdp.ConsumeIntInRange(0, 3)

        if choice == 0:
            # Default mode
            formatted = black.format_str(source_code, mode=Mode())
        elif choice == 1:
            # With line length variation
            line_length = fdp.ConsumeIntInRange(40, 120)
            formatted = black.format_str(source_code, mode=Mode(line_length=line_length))
        elif choice == 2:
            # With different target version
            formatted = black.format_str(source_code, mode=Mode(
                target_versions={TargetVersion.PY310}
            ))
        else:
            # With string normalization off
            formatted = black.format_str(source_code, mode=Mode(
                string_normalization=False
            ))

        # Test idempotence: format(format(x)) == format(x)
        if formatted:
            reformatted = black.format_str(formatted, mode=Mode())
            assert formatted == reformatted, "Black output not idempotent"

    except (black.InvalidInput, ValueError, TypeError, AssertionError):
        # Expected exceptions for invalid Python syntax
        pass
    except RecursionError:
        # Can happen with deeply nested structures
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
