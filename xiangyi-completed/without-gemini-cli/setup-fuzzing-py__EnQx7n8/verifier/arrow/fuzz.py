import atheris
import sys
import arrow

with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))
        arrow.get(s)
    except (ValueError, arrow.parser.ParserError, TypeError):
        pass
    except Exception as e:
        # We might want to catch other exceptions that are not expected
        pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
