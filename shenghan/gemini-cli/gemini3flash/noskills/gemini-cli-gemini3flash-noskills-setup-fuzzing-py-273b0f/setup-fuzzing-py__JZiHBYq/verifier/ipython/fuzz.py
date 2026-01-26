import atheris
import sys
from IPython.core.inputtransformer2 import TransformerManager

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    input_str = fdp.ConsumeUnicodeNoSurrogates(4096)
    tm = TransformerManager()
    try:
        tm.transform_cell(input_str)
    except Exception as e:
        # Most exceptions are fine as it's handling arbitrary input
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
