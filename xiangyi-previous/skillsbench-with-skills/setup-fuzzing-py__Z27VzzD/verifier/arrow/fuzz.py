import atheris
import sys
with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        arrow.get(s)
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
