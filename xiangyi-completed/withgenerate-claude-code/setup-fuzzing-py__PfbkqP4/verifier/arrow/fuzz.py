#!/usr/bin/env python3
"""Coverage-guided fuzzing for Arrow date/time library."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Arrow library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Import arrow inside to ensure instrumentation
    import arrow
    from arrow.parser import ParserError

    # Test 1: Parse arbitrary date/time strings
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(200)
        if date_str:
            arrow.get(date_str)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 2: Parse with format string
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(100)
        format_str = fdp.ConsumeUnicodeNoSurrogates(50)
        if date_str and format_str:
            arrow.get(date_str, format_str)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 3: Parse timestamps (int/float)
    try:
        choice = fdp.ConsumeIntInRange(0, 2)
        if choice == 0:
            ts = fdp.ConsumeFloat()
            arrow.get(ts)
        elif choice == 1:
            ts = fdp.ConsumeInt(8)
            arrow.get(ts)
        else:
            # Consume as string timestamp
            ts_str = fdp.ConsumeUnicodeNoSurrogates(20)
            if ts_str:
                arrow.get(ts_str)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 4: Parse timezone expressions
    try:
        tz_str = fdp.ConsumeUnicodeNoSurrogates(50)
        if tz_str:
            arrow.now(tz_str)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 5: Shift and manipulation on parsed dates
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(100)
        if date_str:
            a = arrow.get(date_str)
            days = fdp.ConsumeIntInRange(-1000, 1000)
            hours = fdp.ConsumeIntInRange(-1000, 1000)
            a.shift(days=days, hours=hours)
    except (ParserError, ValueError, TypeError, OverflowError, OSError, AttributeError):
        pass


def main():
    # Instrument imports
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
