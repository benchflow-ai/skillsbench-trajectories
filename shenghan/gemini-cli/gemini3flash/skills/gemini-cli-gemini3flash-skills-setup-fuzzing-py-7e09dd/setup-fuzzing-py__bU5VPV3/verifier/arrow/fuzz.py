import atheris
import sys

with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz arrow.get with a random string
        input_str = fdp.ConsumeUnicodeNoSurrogates(256)
        arrow.get(input_str)
    except (arrow.parser.ParserError, ValueError, TypeError, OverflowError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
