import atheris
import sys
import black
from black.report import NothingChanged

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeString(sys.maxsize)
    try:
        black.format_str(s, mode=black.Mode())
    except (black.parsing.InvalidInput, ValueError, SyntaxError, NothingChanged):
        pass
    except Exception as e:
        if "cannot be parsed" in str(e):
             pass
        else:
             raise

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
