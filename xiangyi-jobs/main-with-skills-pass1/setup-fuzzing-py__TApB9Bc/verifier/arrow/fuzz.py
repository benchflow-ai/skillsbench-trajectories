#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for Arrow datetime parsing library.
Targets: DateTimeParser.parse_iso() and ArrowFactory.get()
"""

import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser
    from arrow.factory import ArrowFactory

def TestOneInput(data):
    """Fuzz entry point for Arrow library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz target 1: DateTimeParser.parse_iso()
    try:
        parser = DateTimeParser()
        datetime_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
        normalize_ws = fdp.ConsumeBool()
        try:
            parser.parse_iso(datetime_str, normalize_whitespace=normalize_ws)
        except (arrow.parser.ParserError, arrow.parser.ParserMatchError):
            # Expected exceptions - parsing should handle them gracefully
            pass
    except Exception:
        pass

    # Fuzz target 2: ArrowFactory.get()
    try:
        factory = ArrowFactory()

        # Generate random arguments
        arg_type = fdp.ConsumeIntInRange(0, 5)

        if arg_type == 0:
            # Try with timestamp
            ts = fdp.ConsumeFloat()
            try:
                factory.get(ts)
            except (TypeError, ValueError, OverflowError):
                pass
        elif arg_type == 1:
            # Try with string
            date_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
            try:
                factory.get(date_str)
            except (TypeError, ValueError, arrow.parser.ParserError):
                pass
        elif arg_type == 2:
            # Try with multiple arguments
            year = fdp.ConsumeIntInRange(1970, 2100)
            month = fdp.ConsumeIntInRange(1, 12)
            day = fdp.ConsumeIntInRange(1, 28)
            try:
                factory.get(year, month, day)
            except (TypeError, ValueError, IndexError):
                pass
        else:
            # Try with empty or no arguments
            try:
                factory.get()
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
