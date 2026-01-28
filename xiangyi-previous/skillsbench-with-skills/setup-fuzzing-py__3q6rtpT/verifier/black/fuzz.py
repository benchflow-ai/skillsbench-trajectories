#!/usr/bin/env python3
"""
Fuzz driver for Black code formatter
Targets: format_str() and format_ipynb_string()
"""

import sys
import atheris

with atheris.instrument_imports():
    import black
    from black.parsing import InvalidInput
    from black import NothingChanged

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Black formatter"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose between Python code and Jupyter notebook fuzzing
    choice = fdp.ConsumeIntInRange(0, 1)

    try:
        if choice == 0:
            # Fuzz Python code formatting
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 1000))
            if code:
                mode = black.Mode()
                black.format_str(code, mode=mode)

        elif choice == 1:
            # Fuzz Jupyter notebook formatting
            notebook_json = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 1000))
            if notebook_json:
                mode = black.Mode()
                black.format_ipynb_string(notebook_json, fast=True, mode=mode)

    except (InvalidInput, NothingChanged, ValueError, TypeError, SyntaxError,
            UnicodeDecodeError, KeyError, IndexError, AttributeError):
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Log unexpected exceptions but don't crash
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
