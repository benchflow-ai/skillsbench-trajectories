#!/usr/bin/env python3
"""
Fuzzing driver for Arrow library using Atheris (LibFuzzer for Python)
Targets: arrow.get() parsing, format string handling, and timezone conversions
"""

import sys
import atheris

# Suppress warnings for cleaner fuzzing output
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    import arrow
    from arrow import ParserError


def TestOneInput(data):
    """Fuzz target for Arrow library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz arrow.get() with random string
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
            arrow.get(date_string)

        elif choice == 1:
            # Fuzz arrow.get() with format string
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            if date_string and format_string:
                arrow.get(date_string, format_string)

        elif choice == 2:
            # Fuzz arrow.get() with timestamp
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)

        elif choice == 3:
            # Fuzz Arrow.format() with custom format string
            format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            arr = arrow.now()
            arr.format(format_string)

        elif choice == 4:
            # Fuzz with locale
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            locale_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 20))
            if locale_string:
                arrow.get(date_string, locale=locale_string)

    except (ParserError, ValueError, TypeError, OverflowError, OSError, KeyError):
        # Expected exceptions - these are handled properly
        pass
    except AttributeError:
        # Can occur with invalid format strings
        pass
    except Exception as e:
        # Unexpected exceptions might indicate bugs
        error_type = type(e).__name__
        # Allow some known safe exceptions
        if error_type not in ['ArrowParseError', 'IndexError', 'ZeroDivisionError']:
            raise


def main():
    """Main fuzzing entry point."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
