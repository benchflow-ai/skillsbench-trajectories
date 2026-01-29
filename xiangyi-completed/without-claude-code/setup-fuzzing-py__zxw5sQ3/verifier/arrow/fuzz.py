#!/usr/bin/env python3
"""
Atheris-based fuzzer for Arrow library
Targets: date/time parsing functions
"""

import sys
import atheris

# Suppress output for cleaner fuzzing
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError


def TestOneInput(data):
    """Fuzz entry point called by Atheris"""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 5)

    try:
        if choice == 0:
            # Fuzz arrow.get() with string input
            datetime_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            format_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 50))
            normalize = fdp.ConsumeBool()
            arrow.get(datetime_str, format_str, normalize_whitespace=normalize)

        elif choice == 1:
            # Fuzz DateTimeParser.parse_iso()
            parser = DateTimeParser()
            iso_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            normalize = fdp.ConsumeBool()
            parser.parse_iso(iso_str, normalize_whitespace=normalize)

        elif choice == 2:
            # Fuzz DateTimeParser.parse() with custom format
            parser = DateTimeParser()
            datetime_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
            format_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 50))
            normalize = fdp.ConsumeBool()
            parser.parse(datetime_str, format_str, normalize_whitespace=normalize)

        elif choice == 3:
            # Fuzz TzinfoParser.parse()
            tz_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 100))
            TzinfoParser.parse(tz_str)

        elif choice == 4:
            # Fuzz Arrow.dehumanize()
            humanized = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 100))
            locale = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(2, 10))
            arrow.Arrow.now().dehumanize(humanized, locale=locale)

        elif choice == 5:
            # Fuzz arrow.get() with various input types
            input_type = fdp.ConsumeIntInRange(0, 3)
            if input_type == 0:
                # String input
                s = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 100))
                arrow.get(s)
            elif input_type == 1:
                # Timestamp input
                ts = fdp.ConsumeFloat()
                arrow.get(ts)
            elif input_type == 2:
                # Multiple arguments
                year = fdp.ConsumeIntInRange(1, 9999)
                month = fdp.ConsumeIntInRange(1, 12)
                day = fdp.ConsumeIntInRange(1, 31)
                arrow.get(year, month, day)
            else:
                # With timezone
                tz = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 50))
                arrow.get(tz=tz)

    except (ParserError, ValueError, TypeError, OverflowError,
            KeyError, AttributeError, OSError, ImportError):
        # Expected exceptions during fuzzing
        pass
    except Exception as e:
        # Catch unexpected exceptions for debugging
        # Re-raise to find bugs
        if "maximum recursion depth" not in str(e):
            raise


def main():
    """Initialize and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
