import sys
import atheris

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    try:
        val = ujson.loads(data)
        ujson.dumps(val)
    except (ValueError, TypeError):
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
