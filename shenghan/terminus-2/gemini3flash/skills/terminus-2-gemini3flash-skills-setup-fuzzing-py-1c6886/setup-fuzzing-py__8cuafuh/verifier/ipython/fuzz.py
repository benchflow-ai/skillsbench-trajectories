import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        tm = TransformerManager()
        tm.transform_cell(s)
    except Exception as e:
        # We want to catch unexpected exceptions
        print(f"Unexpected exception: {type(e)}: {e}")
        raise e

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
