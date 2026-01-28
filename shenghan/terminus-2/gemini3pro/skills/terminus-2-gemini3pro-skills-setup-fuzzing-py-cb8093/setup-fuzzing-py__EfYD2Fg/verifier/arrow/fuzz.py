import atheris
import sys
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        arrow.get(fdp.ConsumeString(sys.maxsize))
    except (arrow.parser.ParserError, ValueError):
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
