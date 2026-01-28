import sys
import atheris
import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError, TypeError):
        pass
    except Exception as e:
        # Unexpected exceptions could be bugs
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
