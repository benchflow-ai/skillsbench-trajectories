import atheris
import sys
import ujson

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        ujson.loads(s)
    except (ValueError, TypeError):
        pass
    except Exception as e:
        print(f"Unexpected exception: {type(e)}: {e}")
        raise e

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
