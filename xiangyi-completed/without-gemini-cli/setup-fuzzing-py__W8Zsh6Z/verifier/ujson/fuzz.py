import atheris
import sys
with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    try:
        s = data.decode("utf-8")
        obj = ujson.loads(s)
        ujson.dumps(obj)
    except Exception:
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
