import atheris
import sys
import os

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Test loads
        s = fdp.ConsumeUnicodeNoSurrogates(len(data))
        try:
            obj = ujson.loads(s)
            # If loads succeeded, test dumps
            ujson.dumps(obj)
        except (ValueError, OverflowError, TypeError):
            pass
            
    except Exception:
        raise

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
