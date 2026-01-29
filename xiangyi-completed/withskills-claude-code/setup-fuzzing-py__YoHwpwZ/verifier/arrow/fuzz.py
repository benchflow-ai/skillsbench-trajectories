#!/usr/bin/env python3
"""
Atheris-based fuzzer for Arrow library
Targets: arrow.parser.DateTimeParser.parse() and arrow.factory.ArrowFactory.get()
"""

import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow.parser import ParserError

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Arrow date/time parsing"""
    if len(data) == 0:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test arrow.get() with string input
    try:
        date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
        arrow.get(date_string)
    except (ParserError, ValueError, TypeError, OverflowError, AttributeError):
        pass
    except Exception as e:
        # Log unexpected exceptions
        if not isinstance(e, (ParserError, ValueError, TypeError, OverflowError, AttributeError)):
            raise

    # Remaining bytes: test with timestamp
    remaining = fdp.remaining_bytes()
    if remaining >= 4:
        try:
            timestamp = fdp.ConsumeInt(4)
            arrow.get(timestamp)
        except (ParserError, ValueError, TypeError, OverflowError, OSError):
            pass

    # Test arrow.get() with format string
    remaining = fdp.remaining_bytes()
    if remaining >= 10:
        try:
            date_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(5, 20))
            fmt_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(5, 20))
            arrow.get(date_str, fmt_str)
        except (ParserError, ValueError, TypeError, OverflowError, AttributeError):
            pass

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
