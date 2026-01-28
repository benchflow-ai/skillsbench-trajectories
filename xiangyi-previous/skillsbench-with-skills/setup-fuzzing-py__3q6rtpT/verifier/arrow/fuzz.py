#!/usr/bin/env python3
"""
Fuzz driver for Arrow library
Targets: arrow.get() and date/time parsing functions
"""

import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow import ParserError

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Arrow library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test different fuzzing strategies
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz arrow.get() with string input
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            if date_string:
                arrow.get(date_string)

        elif choice == 1:
            # Fuzz arrow.get() with string and format
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
            if date_string and format_string:
                arrow.get(date_string, format_string)

        elif choice == 2:
            # Fuzz arrow.get() with timestamp
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)

        elif choice == 3:
            # Fuzz Arrow.format()
            try:
                arr = arrow.now()
                format_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
                if format_str:
                    arr.format(format_str)
            except:
                pass

        elif choice == 4:
            # Fuzz humanize with locale
            try:
                arr = arrow.now()
                locale_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 20))
                if locale_str:
                    arr.humanize(locale=locale_str)
            except:
                pass

    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Log unexpected exceptions but don't crash the fuzzer
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
