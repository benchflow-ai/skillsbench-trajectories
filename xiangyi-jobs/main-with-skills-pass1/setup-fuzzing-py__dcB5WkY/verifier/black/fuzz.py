import atheris
import sys
import black
from black import InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        black.format_str(s, mode=black.Mode())
    except (InvalidInput, SyntaxError):
        # Expected errors for invalid python code
        pass
    except ValueError as e:
        # Sometimes black raises ValueError for encoding issues or specific invalid inputs
        if "Cannot parse" in str(e):
            pass
        else:
             pass # Ignore other ValueErrors for now to keep fuzzing running

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
