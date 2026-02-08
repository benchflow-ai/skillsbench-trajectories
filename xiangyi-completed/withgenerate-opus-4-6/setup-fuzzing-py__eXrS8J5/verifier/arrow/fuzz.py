import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, ParserError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not text:
        return

    # Fuzz arrow.get() with string input
    try:
        arrow.get(text)
    except (ParserError, ValueError, TypeError, OverflowError, AttributeError):
        pass

    # Fuzz DateTimeParser.parse_iso()
    parser = DateTimeParser()
    try:
        parser.parse_iso(text)
    except (ParserError, ValueError, TypeError, OverflowError, re.error):
        pass

    # Fuzz arrow.get() with format string
    try:
        arrow.get(text, "YYYY-MM-DD")
    except (ParserError, ValueError, TypeError, OverflowError):
        pass

    # Fuzz arrow.get() with fuzzed format string
    try:
        fmt = fdp.ConsumeUnicodeNoSurrogates(20)
        if fmt:
            arrow.get(text, fmt)
    except (ParserError, ValueError, TypeError, OverflowError, AttributeError, KeyError):
        pass


import re

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
