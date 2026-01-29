#!/usr/bin/env python3
"""Fuzz driver for arrow library - date/time parsing."""

import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow.parser import ParserError


def TestOneInput(data: bytes) -> None:
    """Main fuzz target function for arrow library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Parse arbitrary strings with arrow.get()
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 200)
        )
        arrow.get(date_str)
    except (ParserError, ValueError, TypeError, OverflowError):
        pass

    # Test 2: Parse with format string
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 100)
        )
        format_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 50)
        )
        arrow.get(date_str, format_str)
    except (ParserError, ValueError, TypeError, OverflowError, KeyError):
        pass

    # Test 3: Parse with multiple format strings
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 100)
        )
        format1 = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 30)
        )
        format2 = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 30)
        )
        arrow.get(date_str, [format1, format2])
    except (ParserError, ValueError, TypeError, OverflowError, KeyError):
        pass

    # Test 4: Parse timestamps
    try:
        timestamp = fdp.ConsumeFloat()
        arrow.get(timestamp)
    except (ParserError, ValueError, TypeError, OverflowError, OSError):
        pass

    # Test 5: Parse with locale
    try:
        date_str = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 100)
        )
        locale = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 10)
        )
        arrow.get(date_str, locale=locale)
    except (ParserError, ValueError, TypeError, OverflowError, KeyError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
