import sys
import atheris
from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        tm = TransformerManager()
        tm.transform_cell(s)
    except (SyntaxError, RuntimeError):
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
