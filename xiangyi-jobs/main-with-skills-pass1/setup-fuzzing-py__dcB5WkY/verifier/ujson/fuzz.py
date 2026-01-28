import atheris
import sys
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        # Test parsing
        obj = ujson.loads(s)
        # Test encoding if parsing succeeded
        ujson.dumps(obj)
    except ValueError:
        # Expected for invalid JSON
        pass
    except Exception as e:
        # Catch unexpected exceptions but allow execution to continue
        pass

atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
