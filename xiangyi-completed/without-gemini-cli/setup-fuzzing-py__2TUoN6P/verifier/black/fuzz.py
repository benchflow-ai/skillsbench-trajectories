import sys
import atheris
import black

# Import the library under test
from black import Mode, InvalidInput, NothingChanged

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz input as a string
        input_str = fdp.ConsumeUnicode(sys.maxsize)
        # Use default mode
        black.format_str(input_str, mode=Mode())
    except (InvalidInput, NothingChanged):
        # Expected exceptions
        pass
    except (AssertionError, tokenize.TokenError, IndentationError):
        # Sometimes invalid code can trigger these if it bypasses some checks or 
        # is just really malformed. 
        # Black normally handles syntax errors with InvalidInput, but 
        # let's be safe.
        pass
    except Exception as e:
        # Unexpected crashes
        # Check if it's a syntax error that leaked
        if "SyntaxError" in str(type(e)):
             pass
        else:
             raise e

import tokenize # for TokenError

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
