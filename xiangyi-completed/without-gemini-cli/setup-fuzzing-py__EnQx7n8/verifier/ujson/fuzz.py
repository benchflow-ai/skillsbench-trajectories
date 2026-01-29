import atheris
import sys
import ujson

with atheris.instrument_imports():
    import ujson

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 10240))
        ujson.loads(s)
    except (ValueError, OverflowError, TypeError):
        pass
    except Exception as e:
        # Unexpected exceptions could be bugs
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
