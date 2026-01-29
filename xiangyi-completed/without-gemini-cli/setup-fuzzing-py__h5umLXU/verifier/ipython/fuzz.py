import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        tm = TransformerManager()
        tm.transform_cell(s)
    except Exception:
        # Most exceptions are caught by the transformer itself,
        # but we want to catch any that might escape.
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
