#!/usr/bin/env python3
"""Fuzz driver for IPython library - interactive Python shell."""

import sys
import atheris

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.core import guarded_eval
    from IPython.core.completer import IPCompleter


def TestOneInput(data):
    """Fuzz target for IPython library."""
    fdp = atheris.FuzzedDataProvider(data)
    
    try:
        # Test input transformation with random IPython syntax
        if fdp.ConsumeBool():
            cell_input = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
            try:
                tm = TransformerManager()
                tm.transform_cell(cell_input)
            except (SyntaxError, ValueError, TypeError):
                pass
        
        # Test guarded_eval with random expressions
        elif fdp.ConsumeBool():
            expr = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            try:
                guarded_eval.guarded_eval(expr, {})
            except (SyntaxError, ValueError, TypeError, NameError, AttributeError, guarded_eval.GuardRejection):
                pass
        
        # Test with magic command syntax
        elif fdp.ConsumeBool():
            magic_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            magic_args = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            cell = f"%{magic_name} {magic_args}"
            try:
                tm = TransformerManager()
                tm.transform_cell(cell)
            except (SyntaxError, ValueError, TypeError):
                pass
        
        # Test with cell magic syntax
        elif fdp.ConsumeBool():
            magic_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            magic_body = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            cell = f"%%{magic_name}\n{magic_body}"
            try:
                tm = TransformerManager()
                tm.transform_cell(cell)
            except (SyntaxError, ValueError, TypeError):
                pass
        
        # Test with help syntax
        elif fdp.ConsumeBool():
            obj_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            cell = f"{obj_name}?"
            try:
                tm = TransformerManager()
                tm.transform_cell(cell)
            except (SyntaxError, ValueError, TypeError):
                pass
        
        # Test with shell command syntax
        else:
            command = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            cell = f"!{command}"
            try:
                tm = TransformerManager()
                tm.transform_cell(cell)
            except (SyntaxError, ValueError, TypeError):
                pass
                
    except Exception:
        # Catch any unexpected exceptions
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
