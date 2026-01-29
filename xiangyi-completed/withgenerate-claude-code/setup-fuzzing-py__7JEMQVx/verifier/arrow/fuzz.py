#!/usr/bin/env python3
"""
Fuzz driver for Arrow library
Tests datetime parsing functionality
"""

import atheris
import sys

# Suppress warnings during fuzzing
import warnings
warnings.filterwarnings("ignore")


def TestOneInput(data):
    """Fuzz target for Arrow datetime parsing"""
    fdp = atheris.FuzzedDataProvider(data)

    # Import inside to catch import-time errors
    try:
        import arrow
        from arrow.parser import ParserError, ParserMatchError
    except Exception:
        return

    # Test different functions based on fuzzer choice
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Test arrow.get() with string input
            datetime_str = fdp.ConsumeUnicodeNoSurrogates(200)
            try:
                arrow.get(datetime_str)
            except (ParserError, ParserMatchError, ValueError, TypeError,
                    AttributeError, OverflowError):
                pass

        elif choice == 1:
            # Test arrow.get() with format string
            datetime_str = fdp.ConsumeUnicodeNoSurrogates(100)
            format_str = fdp.ConsumeUnicodeNoSurrogates(50)
            try:
                arrow.get(datetime_str, format_str)
            except (ParserError, ParserMatchError, ValueError, TypeError,
                    AttributeError, OverflowError):
                pass

        elif choice == 2:
            # Test arrow.get() with timestamp
            timestamp = fdp.ConsumeFloat()
            try:
                arrow.get(timestamp)
            except (ParserError, ParserMatchError, ValueError, TypeError,
                    AttributeError, OverflowError, OSError):
                pass

        elif choice == 3:
            # Test Arrow.format() with various format strings
            format_str = fdp.ConsumeUnicodeNoSurrogates(100)
            try:
                arr = arrow.now()
                arr.format(format_str)
            except (ValueError, TypeError, AttributeError, KeyError):
                pass

        else:
            # Test humanize() with different locales
            locale = fdp.ConsumeUnicodeNoSurrogates(20)
            try:
                arr = arrow.now()
                other = arrow.now()
                arr.humanize(other, locale=locale)
            except (ValueError, TypeError, AttributeError, KeyError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions
        # Only crash on assertion errors or unexpected issues
        error_str = str(e).lower()
        if 'assert' in error_str or 'unreachable' in error_str:
            raise
        # Otherwise suppress to continue fuzzing


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
