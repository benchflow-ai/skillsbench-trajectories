import sys
import atheris
from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except UnicodeDecodeError:
        return
    
    tm = TransformerManager()
    try:
        tm.transform_cell(s)
    except (SyntaxError, RuntimeError, ValueError):
        pass
    except Exception:
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
