#!/usr/bin/env python3
"""Arrow library fuzzer using Atheris"""

import atheris
import sys

with atheris.instrument_imports():
    import arrow

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz Arrow's parse_iso function"""
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Fuzz DateTimeParser.parse_iso()
        datetime_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 1000))
        normalize_ws = fdp.ConsumeBool()

        try:
            result = arrow.parser.DateTimeParser().parse_iso(
                datetime_string,
                normalize_whitespace=normalize_ws
            )
        except (arrow.parser.ParserError, ValueError, OverflowError):
            # Expected exceptions for invalid input
            pass

        # Fuzz TzinfoParser.parse()
        tz_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 500))
        try:
            tz_result = arrow.parser.TzinfoParser().parse(tz_string)
        except (arrow.parser.ParserError, ValueError, Exception):
            # Expected exceptions for invalid timezone strings
            pass

        # Fuzz DateTimeParser.parse() with format string
        if len(data) > 10:
            format_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
            try:
                parse_result = arrow.parser.DateTimeParser().parse(
                    datetime_string,
                    format_string
                )
            except (arrow.parser.ParserError, ValueError, TypeError):
                # Expected exceptions
                pass

    except Exception:
        # Catch any unexpected exceptions and report them
        raise

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
