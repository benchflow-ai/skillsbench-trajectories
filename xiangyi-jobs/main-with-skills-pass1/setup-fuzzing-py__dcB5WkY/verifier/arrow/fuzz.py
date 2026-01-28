import atheris
import sys
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz arrow.get() with a string input
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError, TypeError):
        # Expected errors for invalid input
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
