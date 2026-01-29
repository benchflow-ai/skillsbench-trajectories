import atheris
import sys
import os
import tokenize

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        tm = TransformerManager()
        s = fdp.ConsumeUnicodeNoSurrogates(len(data))
        try:
            tm.transform_cell(s)
        except (IndentationError, SyntaxError, tokenize.TokenError):
            pass
    except Exception:
        raise

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()