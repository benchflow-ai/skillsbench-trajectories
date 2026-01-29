#!/usr/bin/env python3
"""
Atheris-based fuzzer for IPython
Targets: IPython.core.inputtransformer2.transform_cell() - IPython syntax transformation
"""

import sys
import atheris

with atheris.instrument_imports():
    import IPython
    from IPython.core import inputtransformer2

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for IPython cell transformation"""
    if len(data) == 0:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Generate IPython cell content
    cell_content = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not cell_content:
        return

    try:
        # Transform IPython cell syntax
        # This handles magic commands, shell escapes, etc.
        transformed = inputtransformer2.transform_cell(cell_content)
    except (SyntaxError, ValueError, TypeError, AttributeError):
        # Expected exceptions for invalid input
        pass
    except TokenError:
        # Expected for tokenization errors
        pass
    except Exception as e:
        # Filter out expected exceptions
        if not isinstance(e, (SyntaxError, ValueError, TypeError, AttributeError)):
            # Some exceptions from the tokenizer/parser are expected
            exc_name = type(e).__name__
            if exc_name not in ['TokenError', 'IndentationError', 'TabError']:
                raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    # Import TokenError here to avoid issues
    try:
        from tokenize import TokenError
    except ImportError:
        TokenError = SyntaxError

    main()
