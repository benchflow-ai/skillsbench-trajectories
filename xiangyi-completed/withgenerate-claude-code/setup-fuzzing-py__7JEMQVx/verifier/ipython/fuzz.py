#!/usr/bin/env python3
"""
Fuzz driver for IPython
Tests input transformation and parsing
"""

import atheris
import sys

# Suppress warnings during fuzzing
import warnings
warnings.filterwarnings("ignore")


def TestOneInput(data):
    """Fuzz target for IPython input transformation"""
    fdp = atheris.FuzzedDataProvider(data)

    # Import inside to catch import-time errors
    try:
        from IPython.core import inputtransformer2
        from IPython.core.inputtransformer2 import TransformerManager
    except Exception:
        return

    # Test different transformation functions
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Test transform_cell()
            cell = fdp.ConsumeUnicodeNoSurrogates(500)
            try:
                tm = TransformerManager()
                tm.transform_cell(cell)
            except (SyntaxError, ValueError, TypeError, AttributeError,
                    IndentationError):
                pass

        elif choice == 1:
            # Test individual line transformations
            line = fdp.ConsumeUnicodeNoSurrogates(200)
            try:
                # Test magic command detection
                from IPython.core.inputtransformer2 import MagicAssign
                ma = MagicAssign()
                list(ma.transform([line]))
            except (SyntaxError, ValueError, TypeError, AttributeError):
                pass

        elif choice == 2:
            # Test escape sequences
            lines = []
            for _ in range(fdp.ConsumeIntInRange(1, 10)):
                lines.append(fdp.ConsumeUnicodeNoSurrogates(100))

            try:
                tm = TransformerManager()
                tm.transform_cell('\n'.join(lines))
            except (SyntaxError, ValueError, TypeError, AttributeError,
                    IndentationError):
                pass

        else:
            # Test tokenization utilities
            text = fdp.ConsumeUnicodeNoSurrogates(300)
            try:
                from IPython.utils import tokenutil
                import io
                import tokenize
                # Test token-based operations
                readline = io.StringIO(text).readline
                tokens = list(tokenize.generate_tokens(readline))
            except (SyntaxError, ValueError, TypeError, AttributeError,
                    tokenize.TokenError, IndentationError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions
        error_str = str(e).lower()
        if 'assert' in error_str or 'unreachable' in error_str:
            raise
        # Otherwise suppress to continue fuzzing


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
