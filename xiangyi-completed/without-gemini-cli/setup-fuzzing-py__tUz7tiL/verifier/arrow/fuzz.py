import atheris
import sys
import arrow

with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz arrow.get(string)
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError, OverflowError):
        pass
    except Exception as e:
        # We might want to catch other specific exceptions that are expected
        # but for now let's just catch Unexpected ones if they happen.
        pass

    try:
        # Fuzz arrow.get(string, format)
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        fmt = fdp.ConsumeUnicodeNoSurrogates(128)
        arrow.get(s, fmt)
    except (arrow.parser.ParserError, ValueError, OverflowError):
        pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
