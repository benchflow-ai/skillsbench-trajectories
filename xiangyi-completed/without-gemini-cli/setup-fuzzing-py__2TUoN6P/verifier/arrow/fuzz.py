import sys
import atheris

# Import the library under test
import arrow
from arrow.parser import ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz input as a string
        input_str = fdp.ConsumeUnicode(sys.maxsize)
        arrow.get(input_str)
    except (ParserError, ValueError):
        # Expected exceptions during parsing
        pass
    except Exception as e:
        # Catch-all for unexpected exceptions to help debug, 
        # though in strict fuzzing we might want to let them crash.
        # For now, let's catch standard errors to avoid noise if common, 
        # but re-raise if it looks critical. 
        # Actually, for fuzzing, if it's not a ParserError/ValueError, it might be a bug.
        # But 'arrow.get' can raise other things? 
        # The docs say ParserError (which is a ValueError).
        raise e

def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
