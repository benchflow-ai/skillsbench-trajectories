#!/usr/bin/env python3
"""
Coverage-guided fuzzer for IPython library using Atheris (LibFuzzer).
Targets input transformation and parsing functions.
"""

import sys
import os

# Add IPython to path
sys.path.insert(0, os.path.dirname(__file__))

import atheris

# Enable coverage instrumentation - limit to only needed modules
with atheris.instrument_imports(include=["IPython.core.inputtransformer2", "IPython.utils.tokenutil"]):
    import tokenize
    from io import StringIO
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils.tokenutil import token_at_cursor


def TestOneInput(data):
    """Fuzz target for IPython library."""
    # Need at least some bytes to work with
    if len(data) < 1:
        return

    try:
        input_str = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not input_str:
        return

    # Test 1: TransformerManager.transform_cell() - core transformation
    try:
        manager = TransformerManager()
        manager.transform_cell(input_str)
    except (
        SyntaxError,
        ValueError,
        TypeError,
        IndexError,
        RecursionError,
        MemoryError,
        tokenize.TokenError,
    ):
        pass
    except Exception:
        pass

    # Test 2: token_at_cursor() - token extraction
    try:
        # Test at various cursor positions
        for pos in [0, len(input_str) // 2, len(input_str)]:
            token_at_cursor(input_str, pos)
    except (
        SyntaxError,
        ValueError,
        TypeError,
        IndexError,
    ):
        pass
    except Exception:
        pass

    # Test 3: Test magic-like input patterns
    if input_str.startswith(('%', '!', '?')):
        try:
            manager = TransformerManager()
            manager.transform_cell(input_str)
        except Exception:
            pass

    # Test 4: Test multiline input
    if '\n' in input_str:
        try:
            manager = TransformerManager()
            manager.transform_cell(input_str)
        except Exception:
            pass


def main():
    # Run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
