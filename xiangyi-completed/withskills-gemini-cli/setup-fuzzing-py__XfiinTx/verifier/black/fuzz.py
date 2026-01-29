import sys
import atheris
import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        black.format_str(s, mode=black.Mode())
    except (black.InvalidInput, black.NothingChanged):
        pass
    except (IndentationError, SyntaxError):
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
