import sys
import atheris
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        arrow.get(fdp.ConsumeString(sys.maxsize))
    except (arrow.parser.ParserError, ValueError, TypeError):
        pass
    except Exception as e:
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
