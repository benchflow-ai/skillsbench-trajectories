import atheris
import sys

with atheris.instrument_imports(include=["IPython"]):
    from IPython.core.inputtransformer2 import TransformerManager

# Instantiate once if possible
tm = TransformerManager()

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except UnicodeDecodeError:
        return

    try:
        tm.transform_cell(s)
    except (SyntaxError, ValueError, RuntimeError):
        # Expected errors during parsing/transformation
        pass
    except Exception as e:
        # Unexpected
        # raise e
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()