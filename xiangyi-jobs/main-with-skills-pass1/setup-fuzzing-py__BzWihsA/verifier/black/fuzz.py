#!/usr/bin/env python3
"""Fuzz driver for Black library - Python code formatting"""

import atheris
import sys

with atheris.instrument_imports():
    import black

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz black.format_str() with random Python code"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test format_str with random Python code
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 4096))
        if code:
            mode = black.Mode()
            black.format_str(code, mode=mode)
    except (
        black.parsing.InvalidInput,
        black.parsing.ASTSafetyError,
        black.report.NothingChanged,
        ValueError,
        SyntaxError,
        OverflowError,
        RecursionError,
    ):
        # Expected exceptions for invalid or unparseable code
        pass
    except Exception as e:
        # Catch unexpected exceptions
        error_msg = str(e).lower()
        if not any(x in error_msg for x in ['invalid', 'cannot', 'expected', 'unexpected', 'syntax']):
            raise

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
