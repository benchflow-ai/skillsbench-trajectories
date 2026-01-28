import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    tm = TransformerManager()
    try:
        tm.transform_cell(fdp.ConsumeString(sys.maxsize))
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
