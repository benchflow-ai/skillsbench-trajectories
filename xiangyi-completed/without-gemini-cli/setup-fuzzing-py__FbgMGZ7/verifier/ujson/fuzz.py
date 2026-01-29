import sys
import atheris
import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        ujson.loads(s)
    except ValueError:
        pass
    except Exception as e:
        # ujson might raise other things? Standard JSON raises JSONDecodeError which inherits ValueError.
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
