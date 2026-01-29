import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except Exception:
        return

    try:
        ujson.loads(s)
    except (ValueError, TypeError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
