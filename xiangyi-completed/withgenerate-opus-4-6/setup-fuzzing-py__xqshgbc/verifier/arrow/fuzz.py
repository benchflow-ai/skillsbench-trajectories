"""Coverage-guided fuzz driver for the Arrow date/time library."""
import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 5)

    if choice == 0:
        # Fuzz arrow.get() with a string
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        try:
            arrow.get(s)
        except (ParserError, ValueError, TypeError, OverflowError,
                AttributeError, re.error, OSError):
            pass

    elif choice == 1:
        # Fuzz DateTimeParser.parse_iso()
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        parser = DateTimeParser()
        try:
            parser.parse_iso(s, normalize_whitespace=fdp.ConsumeBool())
        except (ParserError, ValueError, TypeError, OverflowError,
                AttributeError, re.error):
            pass

    elif choice == 2:
        # Fuzz DateTimeParser.parse() with a format string
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
        fmt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        parser = DateTimeParser()
        try:
            parser.parse(s, fmt, normalize_whitespace=fdp.ConsumeBool())
        except (ParserError, ValueError, TypeError, OverflowError,
                AttributeError, re.error):
            pass

    elif choice == 3:
        # Fuzz TzinfoParser.parse()
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
        try:
            TzinfoParser.parse(s)
        except (ParserError, ValueError, TypeError, OverflowError,
                AttributeError, KeyError):
            pass

    elif choice == 4:
        # Fuzz Arrow.format() with a fuzzed format string
        fmt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
        try:
            a = arrow.utcnow()
            a.format(fmt)
        except (ParserError, ValueError, TypeError, OverflowError,
                AttributeError, KeyError, re.error):
            pass

    elif choice == 5:
        # Fuzz Arrow.dehumanize()
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
        try:
            a = arrow.utcnow()
            a.dehumanize(s)
        except (ParserError, ValueError, TypeError, OverflowError,
                AttributeError, KeyError, re.error):
            pass


import re

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
