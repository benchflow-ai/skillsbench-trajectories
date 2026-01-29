import atheris
import sys

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    try:
        s = data.decode("utf-8", "ignore")
        obj = ujson.loads(s)
        ujson.dumps(obj)
    except Exception:
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()