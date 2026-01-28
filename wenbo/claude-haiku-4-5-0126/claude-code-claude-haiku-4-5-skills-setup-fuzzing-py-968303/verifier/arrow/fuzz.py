#!/usr/bin/env python3
"""
Fuzz driver for Arrow library - datetime parsing
Focuses on parse_iso() and parse() functions
"""

import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for Arrow library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Split data to choose fuzzing strategy
    strategy = fdp.ConsumeIntInRange(0, 4)

    if strategy == 0:
        # Fuzz parse_iso()
        try:
            dt_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
            parser = DateTimeParser()
            parser.parse_iso(dt_string)
        except (ValueError, TypeError, arrow.ParserError):
            pass

    elif strategy == 1:
        # Fuzz parse() with format string
        try:
            dt_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
            fmt = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 128))
            parser = DateTimeParser()
            parser.parse(dt_string, fmt)
        except (ValueError, TypeError, arrow.ParserError, IndexError):
            pass

    elif strategy == 2:
        # Fuzz TzinfoParser
        try:
            tz_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
            TzinfoParser.parse(tz_string)
        except (ValueError, TypeError, arrow.ParserError):
            pass

    elif strategy == 3:
        # Fuzz arrow.get() with various inputs
        try:
            dt_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
            arrow.get(dt_string)
        except (ValueError, TypeError, arrow.ParserError):
            pass

    elif strategy == 4:
        # Fuzz with multiple locale formats
        try:
            dt_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
            fmt_choice = fdp.ConsumeIntInRange(0, 3)
            formats = [
                'YYYY-MM-DD',
                'DD/MM/YYYY',
                'YYYY-MM-DD HH:mm:ss',
                'MM-DD-YYYY'
            ]
            parser = DateTimeParser()
            parser.parse(dt_string, formats[fmt_choice])
        except (ValueError, TypeError, arrow.ParserError, IndexError):
            pass


if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
