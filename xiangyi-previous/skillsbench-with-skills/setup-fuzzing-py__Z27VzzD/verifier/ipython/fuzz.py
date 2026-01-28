import atheris
import sys
with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        tm = TransformerManager()
        tm.transform_cell(s)
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
