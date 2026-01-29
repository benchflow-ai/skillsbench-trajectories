import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

tm = TransformerManager()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeString(sys.maxsize)
    try:
        tm.transform_cell(s)
    except (SyntaxError, ValueError, TypeError):
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
