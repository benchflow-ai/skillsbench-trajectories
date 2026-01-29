import atheris
import sys
with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    try:
        s = data.decode("utf-8", errors="ignore")
        tm = TransformerManager()
        tm.transform_cell(s)
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
