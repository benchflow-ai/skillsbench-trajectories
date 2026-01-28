import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

tm = TransformerManager()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        tm.transform_cell(s)
    except (SyntaxError, ValueError, TypeError, RuntimeError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
