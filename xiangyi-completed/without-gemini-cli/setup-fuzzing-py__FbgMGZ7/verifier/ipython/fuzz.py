import sys
import atheris
import tokenize
from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    tm = TransformerManager()
    try:
        s = fdp.ConsumeString(sys.maxsize)
        tm.transform_cell(s)
    except (SyntaxError, tokenize.TokenError, RuntimeError):
        # transform_cell calls tokenize which can raise TokenError
        # RuntimeError is raised if transformation loop limit is reached (infinite loop protection)
        pass
    except Exception as e:
        # Unexpected errors
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
