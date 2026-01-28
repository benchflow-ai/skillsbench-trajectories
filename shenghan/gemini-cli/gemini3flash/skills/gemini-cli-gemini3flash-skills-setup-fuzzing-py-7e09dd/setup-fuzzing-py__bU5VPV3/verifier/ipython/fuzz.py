import atheris
import sys

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        tm = TransformerManager()
        src = fdp.ConsumeUnicodeNoSurrogates(1024)
        tm.transform_cell(src)
        tm.check_complete(src)
    except (SyntaxError, ValueError, RuntimeError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
