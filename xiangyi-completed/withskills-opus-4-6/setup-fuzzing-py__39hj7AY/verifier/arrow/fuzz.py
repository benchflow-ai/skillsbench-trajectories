#!/usr/bin/python3
"""Coverage-guided fuzz driver for the Arrow datetime library.

Targets:
  1. DateTimeParser.parse_iso() - ISO 8601 string parsing
  2. DateTimeParser.parse()     - Format-string-based parsing
  3. TzinfoParser.parse()       - Timezone string parsing
  4. Arrow.dehumanize()         - Natural language time parsing
  5. ArrowFactory.get()         - Main public API entry point
"""
import atheris
import re
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError

# Reusable parser instance
_parser = DateTimeParser()

# Pre-create a base Arrow for dehumanize
_base_arrow = arrow.Arrow(2023, 1, 15, 12, 0, 0)


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Use first byte to select which target to exercise
    if fdp.remaining_bytes() < 2:
        return
    target = fdp.ConsumeIntInRange(0, 4)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if target == 0:
        # Target 1: parse_iso
        try:
            _parser.parse_iso(s)
        except (ParserError, ParserMatchError, ValueError, OverflowError,
                re.error):
            pass

    elif target == 1:
        # Target 2: parse with format string
        if len(s) < 2:
            return
        split_point = len(s) // 2
        datetime_string = s[:split_point]
        fmt = s[split_point:]
        try:
            _parser.parse(datetime_string, fmt)
        except (ParserError, ParserMatchError, ValueError, OverflowError,
                re.error):
            pass

    elif target == 2:
        # Target 3: TzinfoParser.parse
        try:
            TzinfoParser.parse(s)
        except (ParserError, ValueError, OverflowError, KeyError):
            pass

    elif target == 3:
        # Target 4: Arrow.dehumanize
        try:
            _base_arrow.dehumanize(s, locale="en_us")
        except (ValueError, OverflowError, KeyError, re.error):
            pass

    elif target == 4:
        # Target 5: arrow.get (main public API)
        try:
            arrow.get(s)
        except (ParserError, ParserMatchError, TypeError, ValueError,
                OverflowError, re.error):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
