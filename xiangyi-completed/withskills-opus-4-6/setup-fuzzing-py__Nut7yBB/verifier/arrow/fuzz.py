import sys
sys.dont_write_bytecode = True

import atheris
import re

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    from arrow.arrow import Arrow


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which target to exercise based on a consumed byte.
    target = fdp.ConsumeIntInRange(0, 4)

    if target == 0:
        # Target 1: DateTimeParser.parse_iso
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        parser = DateTimeParser()
        try:
            parser.parse_iso(s)
        except (ParserError, ParserMatchError, ValueError, OverflowError):
            pass

    elif target == 1:
        # Target 2: DateTimeParser.parse (two-string input: format + datetime)
        fmt_len = fdp.ConsumeIntInRange(0, 200)
        fmt = fdp.ConsumeUnicodeNoSurrogates(fmt_len)
        dt_str = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        parser = DateTimeParser()
        try:
            parser.parse(dt_str, fmt)
        except (ParserError, ParserMatchError, re.error, ValueError, OverflowError):
            pass

    elif target == 2:
        # Target 3: TzinfoParser.parse
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            TzinfoParser.parse(s)
        except (ParserError, ValueError, OverflowError):
            pass

    elif target == 3:
        # Target 4: Arrow.dehumanize
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        arw = Arrow(2021, 6, 15, 12, 0, 0)
        try:
            arw.dehumanize(s, locale="en_us")
        except (ValueError, OverflowError):
            pass

    elif target == 4:
        # Target 5: arrow.get (public API string path)
        s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            arrow.get(s)
        except (ParserError, TypeError, ValueError, OverflowError):
            pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
