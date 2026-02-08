"""Coverage-guided fuzz driver for the Arrow date/time library."""

import sys
import atheris

def TestOneInput(data: bytes):
    """Fuzz target for arrow date/time parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError

    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
    choice = fdp.ConsumeIntInRange(0, 5)

    try:
        if choice == 0:
            # Fuzz arrow.get() with a string (ISO 8601 parsing)
            arrow.get(text)
        elif choice == 1:
            # Fuzz DateTimeParser.parse_iso()
            parser = DateTimeParser()
            parser.parse_iso(text)
        elif choice == 2:
            # Fuzz DateTimeParser.parse() with a format string
            fmt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
            parser = DateTimeParser()
            parser.parse(text, fmt)
        elif choice == 3:
            # Fuzz TzinfoParser.parse()
            TzinfoParser.parse(text)
        elif choice == 4:
            # Fuzz Arrow.dehumanize()
            now = arrow.utcnow()
            now.dehumanize(text)
        elif choice == 5:
            # Fuzz Arrow.format() with a format string
            now = arrow.utcnow()
            now.format(text)
    except (
        ValueError,
        TypeError,
        OverflowError,
        KeyError,
        AttributeError,
        IndexError,
        ParserError,
        re.error,
    ):
        pass
    except Exception as e:
        # Allow known safe exceptions to pass
        err_name = type(e).__name__
        if err_name in (
            "ParserMatchError",
            "ZoneInfoNotFoundError",
            "InvalidOperation",
        ):
            pass
        else:
            raise

import re

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
