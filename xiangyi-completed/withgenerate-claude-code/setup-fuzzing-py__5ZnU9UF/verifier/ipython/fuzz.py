#!/usr/bin/env python3
"""
Fuzz driver for IPython - Interactive Python shell
Focuses on input transformation and compilation (NOT execution)
"""
import sys
import atheris

# Import after atheris for better instrumentation
with atheris.instrument_imports():
    from IPython.core.compilerop import CachingCompiler
    from IPython.core import inputtransformer2


def TestOneInput(data):
    """Fuzz IPython input processing and compilation"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Input transformation (IPython syntax to Python)
    code_str = fdp.ConsumeUnicodeNoSurrogates(500)
    try:
        # Transform IPython syntax to valid Python
        # This handles magic commands, etc.
        transformed = inputtransformer2.TransformerManager().transform_cell(code_str)
    except (SyntaxError, ValueError, TypeError, IndentationError, AttributeError, KeyError):
        # Expected exceptions for invalid input
        pass
    except RecursionError:
        # Can happen with malformed input
        pass

    # Test 2: Code compilation
    if fdp.remaining_bytes() > 100:
        code_str = fdp.ConsumeUnicodeNoSurrogates(500)
        try:
            compiler = CachingCompiler()
            # Try to compile the code (but don't execute!)
            # Use 'exec' mode for statements
            code_obj = compiler(code_str, '<fuzz>', 'exec')
        except (SyntaxError, ValueError, TypeError, IndentationError, MemoryError, RecursionError):
            # Expected exceptions for invalid code
            pass

    # Test 3: Single line transformation
    if fdp.remaining_bytes() > 50:
        line = fdp.ConsumeUnicodeNoSurrogates(200)
        try:
            # Test single line transformations
            transformed = inputtransformer2.TransformerManager().transform_cell(line)
        except (SyntaxError, ValueError, TypeError, AttributeError, IndentationError, RecursionError):
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
