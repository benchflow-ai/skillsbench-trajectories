#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for Black code formatter.
Targets: format_str() and lib2to3_parse()
"""

import atheris
import sys

with atheris.instrument_imports():
    import black
    from black.parsing import lib2to3_parse

def TestOneInput(data):
    """Fuzz entry point for Black library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz target 1: lib2to3_parse()
    try:
        src_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 4096))
        try:
            lib2to3_parse(src_code)
        except (SyntaxError, ValueError):
            # Expected exceptions for invalid Python syntax
            pass
    except Exception:
        pass

    # Fuzz target 2: format_str()
    try:
        src_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 4096))
        mode = black.FileMode()
        try:
            formatted = black.format_str(src_code, mode=mode)
            # Basic sanity check: formatted code should be string
            assert isinstance(formatted, str)
        except (SyntaxError, ValueError, black.NothingChanged):
            # Expected exceptions
            pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
