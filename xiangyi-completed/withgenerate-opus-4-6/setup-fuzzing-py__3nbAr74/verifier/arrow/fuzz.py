"""Coverage-guided fuzz driver for the Arrow datetime library."""
import sys
import atheris

with atheris.instrument_imports():
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    from arrow.factory import ArrowFactory


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 4)

    if choice == 0:
        # Fuzz parse_iso with arbitrary datetime strings
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        normalize = fdp.ConsumeBool()
        try:
            parser = DateTimeParser()
            parser.parse_iso(text, normalize_whitespace=normalize)
        except (ParserError, ParserMatchError, ValueError, TypeError, OverflowError,
                re.error, KeyError, IndexError):
            pass

    elif choice == 1:
        # Fuzz parse with fuzzed format strings
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
        fmt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        try:
            parser = DateTimeParser()
            parser.parse(text, fmt)
        except (ParserError, ParserMatchError, ValueError, TypeError, OverflowError,
                re.error, KeyError, IndexError):
            pass

    elif choice == 2:
        # Fuzz TzinfoParser
        tz_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        try:
            TzinfoParser.parse(tz_str)
        except (ParserError, ValueError, TypeError, KeyError):
            pass

    elif choice == 3:
        # Fuzz ArrowFactory.get with string input
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
        try:
            factory = ArrowFactory()
            factory.get(text)
        except (ParserError, ParserMatchError, ValueError, TypeError,
                OverflowError, OSError, re.error, KeyError, IndexError):
            pass

    else:
        # Fuzz parse with list of formats
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
        num_fmts = fdp.ConsumeIntInRange(1, 5)
        fmts = [fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
                for _ in range(num_fmts)]
        try:
            parser = DateTimeParser()
            parser.parse(text, fmts)
        except (ParserError, ParserMatchError, ValueError, TypeError, OverflowError,
                re.error, KeyError, IndexError):
            pass


import re

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
