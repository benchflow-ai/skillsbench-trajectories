import atheris
import sys
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
