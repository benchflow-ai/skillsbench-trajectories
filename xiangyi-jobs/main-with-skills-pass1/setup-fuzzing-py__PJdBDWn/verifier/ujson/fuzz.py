import atheris
import sys
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        b = fdp.ConsumeBytes(sys.maxsize)
        ujson.loads(b)
    except (ValueError, TypeError, OverflowError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
