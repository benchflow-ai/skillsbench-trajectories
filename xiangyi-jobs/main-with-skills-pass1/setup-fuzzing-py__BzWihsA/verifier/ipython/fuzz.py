#!/usr/bin/env python3
"""Fuzz driver for IPython library - input transformation"""

import atheris
import sys
import io

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core import compilerop

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz IPython input transformation"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test input transformer
    try:
        code = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2048))
        if code:
            transformer = TransformerManager()
            transformer.transform_cell(code)
    except (SyntaxError, ValueError, TypeError, AttributeError, RecursionError):
        # Expected exceptions for malformed input
        pass
    except Exception as e:
        error_msg = str(e).lower()
        if not any(x in error_msg for x in ['invalid', 'unexpected', 'cannot', 'bad', 'incomplete']):
            raise

    # Test compiler
    try:
        remaining = fdp.remaining_bytes()
        if remaining > 0:
            code2 = fdp.ConsumeUnicodeNoSurrogates(remaining)
            if code2:
                compiler = compilerop.CachingCompiler()
                compiler(code2, '<fuzz>', 'exec')
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
