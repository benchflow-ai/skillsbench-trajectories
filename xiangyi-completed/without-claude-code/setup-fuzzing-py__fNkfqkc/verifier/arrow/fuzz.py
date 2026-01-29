#!/usr/bin/env python3
"""
LibFuzzer-style fuzz driver for Arrow library using Atheris.
Tests date/time parsing and manipulation functions.
"""

import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser


def TestOneInput(data):
    """Fuzz target for Arrow library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Skip empty inputs
    if len(data) < 1:
        return

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 5)

    try:
        if choice == 0:
            # Fuzz arrow.get() with string input
            date_string = fdp.ConsumeUnicodeNoSurrogates(100)
            if date_string:
                try:
                    arrow.get(date_string)
                except (ValueError, TypeError, arrow.parser.ParserError):
                    pass

        elif choice == 1:
            # Fuzz arrow.get() with format string
            date_string = fdp.ConsumeUnicodeNoSurrogates(50)
            format_string = fdp.ConsumeUnicodeNoSurrogates(50)
            if date_string and format_string:
                try:
                    arrow.get(date_string, format_string)
                except (ValueError, TypeError, arrow.parser.ParserError):
                    pass

        elif choice == 2:
            # Fuzz DateTimeParser.parse_iso()
            parser = DateTimeParser()
            iso_string = fdp.ConsumeUnicodeNoSurrogates(100)
            if iso_string:
                try:
                    parser.parse_iso(iso_string)
                except (ValueError, TypeError, arrow.parser.ParserError):
                    pass

        elif choice == 3:
            # Fuzz Arrow.format() with format string
            try:
                arr = arrow.utcnow()
                format_str = fdp.ConsumeUnicodeNoSurrogates(100)
                if format_str:
                    arr.format(format_str)
            except (ValueError, TypeError, KeyError):
                pass

        elif choice == 4:
            # Fuzz Arrow.shift() with random kwargs
            try:
                arr = arrow.utcnow()
                # Generate random shift parameters
                shift_params = {}
                param_names = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
                for param in param_names:
                    if fdp.ConsumeBool():
                        shift_params[param] = fdp.ConsumeIntInRange(-1000, 1000)
                if shift_params:
                    arr.shift(**shift_params)
            except (ValueError, TypeError, AttributeError):
                pass

        elif choice == 5:
            # Fuzz Arrow.humanize() with locale
            try:
                arr = arrow.utcnow()
                locale = fdp.ConsumeUnicodeNoSurrogates(20)
                if locale:
                    arr.humanize(locale=locale)
            except (ValueError, TypeError, KeyError):
                pass

    except Exception as e:
        # Allow expected exceptions but catch unexpected crashes
        if not isinstance(e, (ValueError, TypeError, KeyError, AttributeError,
                            arrow.parser.ParserError, OverflowError)):
            raise


def main():
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
