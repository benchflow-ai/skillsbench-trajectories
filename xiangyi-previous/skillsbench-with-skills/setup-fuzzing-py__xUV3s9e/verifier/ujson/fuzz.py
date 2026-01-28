import atheris
import sys
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        ujson.loads(fdp.ConsumeString(sys.maxsize))
    except (ValueError, TypeError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
