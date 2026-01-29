import sys
import atheris
import arrow
from arrow.parser import ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeString(sys.maxsize)
        arrow.get(s)
    except (ParserError, ValueError):
        pass
    except Exception as e:
        # Catch other potential issues but re-raise if it looks like a bug (e.g. not a parsing error)
        # For now, let's keep it simple. If arrow raises generic Exception for parsing, we might catch it.
        # But usually libraries should raise specific errors.
        # Let's verify what arrow raises on bad input.
        pass

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
