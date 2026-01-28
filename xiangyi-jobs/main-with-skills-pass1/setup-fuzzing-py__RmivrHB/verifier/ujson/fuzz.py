import sys
import atheris
import ujson

def TestOneInput(data):
    try:
        s = data.decode("utf-8", "ignore")
        obj = ujson.loads(s)
        ujson.dumps(obj)
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
