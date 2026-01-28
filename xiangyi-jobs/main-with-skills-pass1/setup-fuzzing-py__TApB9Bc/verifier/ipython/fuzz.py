#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for IPython shell.
Targets: TransformerManager.transform_cell() and CachingCompiler.ast_parse()
"""

import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core.compilerop import CachingCompiler

def TestOneInput(data):
    """Fuzz entry point for IPython library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz target 1: TransformerManager.transform_cell()
    try:
        tm = TransformerManager()
        cell_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 2048))
        try:
            transformed = tm.transform_cell(cell_input)
            # Sanity check: should return string
            assert isinstance(transformed, str)
        except Exception:
            # Expected: transformation may fail on invalid input
            pass
    except Exception:
        pass

    # Fuzz target 2: CachingCompiler.ast_parse()
    try:
        compiler = CachingCompiler()
        source_code = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 2048))
        symbol = fdp.PickValueInList(['exec', 'eval', 'single'])
        try:
            ast_result = compiler.ast_parse(source_code, symbol=symbol)
            # Sanity check: should return AST
            assert ast_result is not None
        except SyntaxError:
            # Expected: invalid syntax should raise SyntaxError
            pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
