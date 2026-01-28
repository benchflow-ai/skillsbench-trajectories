import atheris
import sys
import black
from black.parsing import InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        black.format_str(s, mode=black.Mode())
    except (InvalidInput, SyntaxError, IndentationError, TypeError, ValueError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
