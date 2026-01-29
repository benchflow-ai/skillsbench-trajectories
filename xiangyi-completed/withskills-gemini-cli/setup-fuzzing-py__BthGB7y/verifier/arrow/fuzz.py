import sys
import atheris

with atheris.instrument_imports():
    from arrow.parser import DateTimeParser, ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicode(sys.maxsize)
    except Exception:
        return

    parser = DateTimeParser()
    try:
        parser.parse_iso(s)
    except (ParserError, ValueError):
        pass
    except Exception as e:
        # We want to find unexpected exceptions
        raise e

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
