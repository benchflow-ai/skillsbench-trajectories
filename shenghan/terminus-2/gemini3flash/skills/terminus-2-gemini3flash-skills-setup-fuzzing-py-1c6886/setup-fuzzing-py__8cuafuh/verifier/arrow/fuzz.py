import atheris
import sys
import arrow

with atheris.instrument_imports():
    import arrow

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        arrow.get(s)
    except (arrow.parser.ParserError, ValueError, TypeError):
        pass
    except Exception as e:
        # We want to catch unexpected exceptions
        print(f"Unexpected exception: {type(e)}: {e}")
        raise e

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
