#!/usr/bin/env python3
"""
Fuzz driver for Arrow library - datetime parsing and formatting
Uses Atheris (LibFuzzer-based) for coverage-guided fuzzing
"""

import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow import ParserError

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Arrow library"""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    if choice == 0:
        # Fuzz arrow.get() with string input
        try:
            date_string = fdp.ConsumeUnicodeNoSurrogates(100)
            if date_string:
                arrow.get(date_string)
        except (ParserError, ValueError, TypeError, OverflowError):
            pass

    elif choice == 1:
        # Fuzz arrow.get() with timestamp
        try:
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)
        except (ParserError, ValueError, TypeError, OverflowError, OSError):
            pass

    elif choice == 2:
        # Fuzz format with custom format string
        try:
            format_string = fdp.ConsumeUnicodeNoSurrogates(50)
            if format_string:
                now = arrow.utcnow()
                now.format(format_string)
        except (ValueError, TypeError, KeyError):
            pass

    elif choice == 3:
        # Fuzz factory.get() with string and format
        try:
            date_string = fdp.ConsumeUnicodeNoSurrogates(50)
            format_string = fdp.ConsumeUnicodeNoSurrogates(30)
            if date_string and format_string:
                factory = arrow.arrow.ArrowFactory()
                factory.get(date_string, format_string)
        except (ParserError, ValueError, TypeError, OverflowError):
            pass

    elif choice == 4:
        # Fuzz humanize with different locales
        try:
            locale = fdp.ConsumeUnicodeNoSurrogates(10)
            now = arrow.utcnow()
            if locale:
                now.humanize(locale=locale)
            else:
                now.humanize()
        except (ValueError, TypeError, KeyError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
