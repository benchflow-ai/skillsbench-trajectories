import sys
import atheris
import tokenize

# Import the library under test
from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz input as a string
        input_str = fdp.ConsumeUnicode(sys.maxsize)
        
        tm = TransformerManager()
        tm.transform_cell(input_str)
    except (SyntaxError, RuntimeError, tokenize.TokenError, ValueError):
        # Expected exceptions:
        # SyntaxError: Invalid Python/IPython syntax
        # RuntimeError: Infinite loop in transformation (caught by limit)
        # TokenError: Tokenization issues
        # ValueError: encoding errors etc
        pass
    except Exception as e:
        # Unexpected crashes
        raise e

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
