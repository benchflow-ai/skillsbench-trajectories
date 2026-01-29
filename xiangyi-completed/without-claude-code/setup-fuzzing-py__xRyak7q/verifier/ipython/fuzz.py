#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for IPython using atheris.

This fuzzer targets key input transformation and parsing functions:
1. TransformerManager.transform_cell() - Main cell transformation
2. TransformerManager.check_complete() - Code completeness checking
3. split_user_input() - Input parsing
"""

import atheris
import sys

# Use instrument_imports() for faster startup
with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.splitinput import split_user_input


def TestOneInput(data: bytes) -> None:
    """Fuzz test function that processes arbitrary input data."""
    # Convert bytes to string using surrogateescape for handling invalid UTF-8
    try:
        input_str = data.decode('utf-8', errors='surrogateescape')
    except Exception:
        return

    # Create a TransformerManager instance
    tm = TransformerManager()

    # Test transform_cell() - Main cell transformation
    try:
        tm.transform_cell(input_str)
    except Exception:
        pass

    # Test check_complete() - Code completeness checking
    try:
        tm.check_complete(input_str)
    except Exception:
        pass

    # Test split_user_input() - Input parsing
    try:
        split_user_input(input_str)
    except Exception:
        pass


if __name__ == "__main__":
    # Setup and run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
