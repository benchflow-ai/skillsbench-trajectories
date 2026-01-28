import atheris
import sys
import arrow
from arrow.parser import ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        arrow.get(s)
    except (ParserError, ValueError, TypeError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
