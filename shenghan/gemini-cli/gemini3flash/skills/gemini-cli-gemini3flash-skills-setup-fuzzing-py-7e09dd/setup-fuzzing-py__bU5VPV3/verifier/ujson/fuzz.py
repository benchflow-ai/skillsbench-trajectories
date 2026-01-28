import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    try:
        ujson.loads(data)
    except (ValueError, TypeError, OverflowError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
