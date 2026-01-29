import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    tm = TransformerManager()
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10240))
        tm.transform_cell(s)
        tm.check_complete(s)
    except Exception as e:
        # Unexpected exceptions could be bugs
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
