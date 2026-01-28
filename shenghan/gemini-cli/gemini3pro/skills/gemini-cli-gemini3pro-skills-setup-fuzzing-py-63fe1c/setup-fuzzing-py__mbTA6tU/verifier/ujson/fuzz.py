import atheris
import sys
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except UnicodeDecodeError:
        return

    try:
        obj = ujson.loads(s)
    except ValueError:
        return
    except Exception as e:
        # Unexpected parse error?
        return

    try:
        ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError):
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
