import atheris
import sys
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        ujson.loads(s)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
