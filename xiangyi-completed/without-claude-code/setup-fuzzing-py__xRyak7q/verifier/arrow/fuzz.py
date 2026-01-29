"""
LibFuzzer-compatible fuzz driver for arrow library using atheris.

This driver performs coverage-guided fuzzing on arrow's key parsing functions:
1. arrow.get() - Primary entry point for parsing datetime strings
2. arrow.parser.DateTimeParser.parse_iso() - ISO 8601 parsing
3. arrow.parser.DateTimeParser.parse() - Custom format parsing
4. arrow.parser.TzinfoParser.parse() - Timezone parsing
5. arrow.Arrow.dehumanize() - Natural language time parsing
"""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz test target function called by atheris for each input."""
    # Convert bytes to string using surrogateescape to handle arbitrary bytes
    try:
        input_str = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return

    # Skip empty inputs
    if not input_str:
        return

    # Import arrow inside the function to ensure instrumentation
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser

    # 1. Fuzz arrow.get() - Primary entry point for parsing datetime strings
    try:
        arrow.get(input_str)
    except (
        arrow.parser.ParserError,
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
        OSError,
    ):
        pass

    # 2. Fuzz DateTimeParser.parse_iso() - ISO 8601 parsing
    parser = DateTimeParser()
    try:
        parser.parse_iso(input_str)
    except (
        arrow.parser.ParserError,
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
    ):
        pass

    # Also test with normalize_whitespace=True
    try:
        parser.parse_iso(input_str, normalize_whitespace=True)
    except (
        arrow.parser.ParserError,
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
    ):
        pass

    # 3. Fuzz DateTimeParser.parse() - Custom format parsing
    # Use the input string as both the datetime string and format pattern
    try:
        parser.parse(input_str, input_str)
    except (
        arrow.parser.ParserError,
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
        re.error,
    ):
        pass

    # Also test with common format patterns
    common_formats = [
        "YYYY-MM-DD",
        "YYYY-MM-DD HH:mm:ss",
        "DD/MM/YYYY",
        "MM-DD-YYYY",
    ]
    for fmt in common_formats:
        try:
            parser.parse(input_str, fmt)
        except (
            arrow.parser.ParserError,
            arrow.parser.ParserMatchError,
            ValueError,
            TypeError,
            OverflowError,
        ):
            pass

    # 4. Fuzz TzinfoParser.parse() - Timezone parsing
    tz_parser = TzinfoParser()
    try:
        tz_parser.parse(input_str)
    except (
        arrow.parser.ParserError,
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
        KeyError,
    ):
        pass

    # 5. Fuzz Arrow.dehumanize() - Natural language time parsing
    now = arrow.now()
    try:
        now.dehumanize(input_str)
    except (
        arrow.parser.ParserError,
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
    ):
        pass

    # Test dehumanize with different locales
    locales_to_test = ["en", "en_us", "de", "fr"]
    for locale in locales_to_test:
        try:
            now.dehumanize(input_str, locale=locale)
        except (
            arrow.parser.ParserError,
            arrow.parser.ParserMatchError,
            ValueError,
            TypeError,
            OverflowError,
            KeyError,
        ):
            pass


# Need to import re for exception handling in parse()
import re


if __name__ == "__main__":
    # Instrument all imports for coverage-guided fuzzing
    atheris.instrument_all()

    # Setup atheris with command line arguments
    atheris.Setup(sys.argv, TestOneInput)

    # Start fuzzing
    atheris.Fuzz()
