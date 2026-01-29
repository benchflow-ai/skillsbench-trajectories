#!/usr/bin/env python3
"""
Fuzz driver for IPython library using atheris.

Tests:
- Code execution and parsing
- Object inspection
- Input transformation
"""

import sys
import atheris
from typing import List


def fuzz_ipython_interactive(data: bytes) -> None:
    """Fuzz IPython interactive shell functions."""
    try:
        from IPython.core.interactiveshell import InteractiveShell
        from IPython.core.inputtransformer2 import TransformerManager

        # Create an InteractiveShell instance
        shell = InteractiveShell.instance()

        # Decode input to string
        if len(data) > 0:
            try:
                code = data.decode('utf-8', errors='ignore')
            except Exception:
                return

            # Test run_cell
            try:
                shell.run_cell(code)
            except Exception:
                pass

            # Test object inspection
            try:
                shell.object_inspect(code)
            except Exception:
                pass

            # Test input transformation
            try:
                tm = TransformerManager()
                lines = code.split('\n')
                result = tm.transform_cell(lines[0]) if lines else ''
            except Exception:
                pass

    except ImportError:
        # Library not installed
        pass


def fuzz_ipython_formatters(data: bytes) -> None:
    """Fuzz IPython formatter functions."""
    try:
        from IPython.core.formatters import FormatterBase

        # Create a basic formatter
        formatter = FormatterBase()

        # Test format function
        try:
            result = formatter.format(data.decode('utf-8', errors='ignore'))
        except Exception:
            pass

    except ImportError:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing entry point."""
    fuzz_ipython_interactive(data)
    fuzz_ipython_formatters(data)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Fuzz driver for IPython library")
        print("Usage: python fuzz.py")
        sys.exit(0)

    atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
    atheris.Fuzz()
