import sys
import atheris
from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        tm = TransformerManager()
        tm.transform_cell(s)
    except Exception as e:
        # Unexpected exceptions could be bugs
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
