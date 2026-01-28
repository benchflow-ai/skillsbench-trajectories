import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

tm = TransformerManager()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        tm.transform_cell(fdp.ConsumeString(sys.maxsize))
    except Exception:
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
