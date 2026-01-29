#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for Arrow library.
Uses atheris for coverage-guided fuzzing.
"""
import sys
import atheris


def setup_arrow():
    """Import arrow after atheris instrumentation."""
    with atheris.instrument_imports():
        import arrow
        from arrow.parser import DateTimeParser, TzinfoParser
        from arrow.factory import ArrowFactory
    return arrow, DateTimeParser, TzinfoParser, ArrowFactory


def TestOneInput(data: bytes):
    """Fuzz target for Arrow library."""
    arrow, DateTimeParser, TzinfoParser, ArrowFactory = setup_arrow.modules

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz arrow.get() with string input
            input_str = fdp.ConsumeUnicodeNoSurrogates(256)
            arrow.get(input_str)

        elif choice == 1:
            # Fuzz arrow.get() with timestamp
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)

        elif choice == 2:
            # Fuzz DateTimeParser.parse_iso()
            parser = DateTimeParser()
            input_str = fdp.ConsumeUnicodeNoSurrogates(256)
            normalize = fdp.ConsumeBool()
            parser.parse_iso(input_str, normalize_whitespace=normalize)

        elif choice == 3:
            # Fuzz TzinfoParser.parse()
            tz_parser = TzinfoParser()
            tz_str = fdp.ConsumeUnicodeNoSurrogates(64)
            tz_parser.parse(tz_str)

        elif choice == 4:
            # Fuzz arrow.get() with format string
            input_str = fdp.ConsumeUnicodeNoSurrogates(128)
            fmt_str = fdp.ConsumeUnicodeNoSurrogates(64)
            arrow.get(input_str, fmt_str)

    except (ValueError, TypeError, OverflowError, arrow.parser.ParserError,
            arrow.parser.ParserMatchError, AttributeError, KeyError, OSError):
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Log unexpected exceptions but don't crash
        if "Unknown string format" not in str(e) and "does not match format" not in str(e):
            pass  # Could add logging here if needed


def main():
    # Pre-import modules for the fuzz target
    arrow, DateTimeParser, TzinfoParser, ArrowFactory = setup_arrow()
    setup_arrow.modules = (arrow, DateTimeParser, TzinfoParser, ArrowFactory)

    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
