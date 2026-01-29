import atheris

with atheris.instrument_imports():
    import sys
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
        arrow.get(s)
    except (arrow.ParserError, ValueError, TypeError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()