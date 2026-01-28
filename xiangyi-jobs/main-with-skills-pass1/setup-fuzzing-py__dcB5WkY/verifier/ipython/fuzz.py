import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

tm = TransformerManager()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        tm.transform_cell(s)
    except (SyntaxError, ValueError, IndexError, RuntimeError):
        # Expected errors for invalid input or transformation limits
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
