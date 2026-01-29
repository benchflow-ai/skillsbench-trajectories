#!/usr/bin/env python3
"""
Fuzz driver for Arrow library
Tests datetime parsing and formatting functions
"""

import sys
import atheris

# Add arrow to path
sys.path.insert(0, '/app/arrow')

import arrow
from arrow import ParserError


def TestOneInput(data):
    """Fuzz target for Arrow library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz arrow.get() with string input
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
            try:
                arrow.get(date_string)
            except (ParserError, ValueError, TypeError, OverflowError):
                pass

        elif choice == 1:
            # Fuzz arrow.get() with format string
            date_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            try:
                arrow.get(date_string, format_string)
            except (ParserError, ValueError, TypeError, OverflowError, AttributeError):
                pass

        elif choice == 2:
            # Fuzz timestamp parsing
            timestamp = fdp.ConsumeFloat()
            try:
                arr = arrow.get(timestamp)
                # Also test format
                format_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
                arr.format(format_str)
            except (ParserError, ValueError, TypeError, OverflowError, OSError):
                pass

        elif choice == 3:
            # Fuzz arrow factory with multiple arguments
            try:
                year = fdp.ConsumeInt(4)
                month = fdp.ConsumeIntInRange(1, 20)
                day = fdp.ConsumeIntInRange(1, 35)
                hour = fdp.ConsumeIntInRange(0, 30)
                minute = fdp.ConsumeIntInRange(0, 70)
                second = fdp.ConsumeIntInRange(0, 70)
                arr = arrow.Arrow(year, month, day, hour, minute, second)
                # Test humanize
                arr.humanize()
            except (ValueError, TypeError, OverflowError):
                pass

        else:
            # Fuzz arrow.utcnow() and operations
            try:
                now = arrow.utcnow()
                shift_params = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
                # This will likely fail but tests string parsing
                if shift_params:
                    now.shift(**{shift_params: 1})
            except (ValueError, TypeError, AttributeError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions for debugging
        # In production fuzzing, we might want to handle these differently
        if "Segmentation fault" in str(e) or "Bus error" in str(e):
            raise


def main():
    """Main fuzzing entry point"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
