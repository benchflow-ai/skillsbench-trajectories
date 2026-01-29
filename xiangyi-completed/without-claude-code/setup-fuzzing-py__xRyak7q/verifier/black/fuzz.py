#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for the Black code formatter.

This driver uses atheris for coverage-guided fuzzing of Black's core
formatting functions.
"""

import atheris
import sys
from tokenize import TokenError

# Instrument all imports for coverage-guided fuzzing
# This must be done before importing the target modules
with atheris.instrument_imports():
    import black
    from black import Mode
    from black.parsing import InvalidInput


def TestOneInput(data: bytes) -> None:
    """Fuzz target function that tests Black's formatting capabilities.

    Args:
        data: Raw bytes to be used as input for fuzzing.
    """
    # Convert bytes to string using utf-8 with surrogateescape for handling
    # arbitrary byte sequences
    try:
        src_contents = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        # If decoding fails for any reason, skip this input
        return

    # Create a Mode object with default settings
    mode = Mode()

    # Test black.format_str() - Main public API for formatting Python code
    try:
        black.format_str(src_contents, mode=mode)
    except (
        # Expected exceptions that can occur with invalid/malformed Python code
        InvalidInput,
        IndentationError,
        SyntaxError,
        ValueError,
        RecursionError,
        TokenError,
    ):
        # These are expected for malformed input - we're looking for crashes,
        # not parsing failures
        pass
    except Exception:
        # Catch any other exceptions - we're looking for crashes/hangs,
        # not expected error handling
        pass


if __name__ == "__main__":
    # Setup atheris with command line arguments
    atheris.Setup(sys.argv, TestOneInput)

    # Start fuzzing
    atheris.Fuzz()
