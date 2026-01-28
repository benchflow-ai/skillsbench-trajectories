import atheris
import sys
import arrow
from arrow.parser import ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except UnicodeDecodeError:
        return

    try:
        arrow.get(s)
    except (ParserError, ValueError, TypeError):
        # Expected errors during parsing
        pass
    except Exception as e:
        # Unexpected errors
        raise e

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
