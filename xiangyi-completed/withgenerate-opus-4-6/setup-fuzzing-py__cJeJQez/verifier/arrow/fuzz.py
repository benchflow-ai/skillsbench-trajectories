"""Coverage-guided fuzz driver for the Arrow library.

Targets:
- arrow.get() with string inputs (ISO parsing, format parsing)
- arrow.parser.TzinfoParser.parse() for timezone string parsing
- arrow.parser.DateTimeParser.parse_iso() for ISO 8601 strings
"""
import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not text:
        return

    try:
        if choice == 0:
            # Fuzz arrow.get() with a string - main entry point
            arrow.get(text)
        elif choice == 1:
            # Fuzz ISO 8601 parsing directly
            parser = DateTimeParser()
            parser.parse_iso(text)
        elif choice == 2:
            # Fuzz timezone string parsing
            tz_parser = TzinfoParser()
            tz_parser.parse(text)
        else:
            # Fuzz arrow.get() with a format string
            fmt = fdp.ConsumeUnicodeNoSurrogates(20) if fdp.remaining_bytes() > 0 else "YYYY-MM-DD"
            arrow.get(text, fmt)
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        OverflowError,
        ParserError,
        AttributeError,
        re.error,
    ):
        pass


import re

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
