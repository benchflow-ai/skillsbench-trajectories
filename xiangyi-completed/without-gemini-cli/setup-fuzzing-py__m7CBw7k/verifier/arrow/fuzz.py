import atheris
import sys
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeString(sys.maxsize)
    try:
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError, TypeError):
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
