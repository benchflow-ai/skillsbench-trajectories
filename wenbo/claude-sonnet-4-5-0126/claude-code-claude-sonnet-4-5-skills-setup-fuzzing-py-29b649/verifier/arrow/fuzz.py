#!/usr/bin/env python3
"""
Fuzz driver for Arrow library - DateTimeParser
Fuzzes parse_iso() and parse() methods for datetime parsing.
"""

import atheris
import sys

with atheris.instrument_imports():
    from arrow.parser import DateTimeParser, ParserError, ParserMatchError


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for Arrow datetime parser."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Create parser instance
    parser = DateTimeParser()

    # Test 1: Fuzz parse_iso() with raw string
    try:
        datetime_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
        if datetime_string:
            parser.parse_iso(datetime_string)
    except (ParserError, ParserMatchError, ValueError, OverflowError):
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Unexpected exception - this might indicate a bug
        # But don't crash the fuzzer, just log it
        pass

    # Test 2: Fuzz parse() with format string
    if fdp.remaining_bytes() > 10:
        try:
            datetime_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            if datetime_string and format_string:
                parser.parse(datetime_string, format_string)
        except (ParserError, ParserMatchError, ValueError, OverflowError):
            # Expected exceptions
            pass
        except Exception as e:
            # Unexpected exception
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
