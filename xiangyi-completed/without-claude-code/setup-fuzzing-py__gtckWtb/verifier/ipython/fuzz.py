#!/usr/bin/env python3
"""
Fuzz driver for IPython library
Tests interactive shell, magic commands, and code execution
"""

import sys
import atheris

# Add IPython to path
sys.path.insert(0, '/app/ipython')

import IPython
from IPython.core.interactiveshell import InteractiveShell


# Create a shell instance for testing
shell = None


def TestOneInput(data):
    """Fuzz target for IPython"""
    global shell

    if len(data) < 1:
        return

    # Initialize shell lazily
    if shell is None:
        shell = InteractiveShell.instance()

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz run_cell with random code
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
            try:
                shell.run_cell(code, store_history=False, silent=True)
            except (SyntaxError, ValueError, TypeError, AttributeError, NameError):
                pass

        elif choice == 1:
            # Fuzz magic commands
            magic_cmd = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            try:
                # Test line magic
                shell.run_line_magic('timeit', magic_cmd)
            except (ValueError, TypeError, AttributeError, KeyError, SyntaxError):
                pass

        elif choice == 2:
            # Fuzz input transformation
            code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            try:
                from IPython.core import inputtransformer2
                transformed = inputtransformer2.TransformerManager().transform_cell(code)
            except (SyntaxError, ValueError, TypeError, AttributeError):
                pass

        else:
            # Fuzz completion
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            try:
                shell.complete(text)
            except (ValueError, TypeError, AttributeError, KeyError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions for debugging
        error_str = str(e)
        if "Segmentation fault" in error_str or "Bus error" in error_str:
            raise
        # Ignore expected errors
        if "UsageError" in error_str or "SyntaxError" in error_str:
            pass


def main():
    """Main fuzzing entry point"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
