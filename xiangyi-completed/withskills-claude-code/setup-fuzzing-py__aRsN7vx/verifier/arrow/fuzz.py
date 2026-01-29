#!/usr/bin/env python3
"""
Fuzz driver for Arrow datetime parsing library.
Targets the main parsing functions with various inputs to find edge cases and bugs.
"""

import sys
import atheris

with atheris.instrument_imports():
    from arrow import parser
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError


def TestOneInput(data):
    """Fuzz entry point for Arrow parser functions."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz DateTimeParser.parse_iso()
            datetime_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            normalize_ws = fdp.ConsumeBool()

            parser_instance = DateTimeParser()
            try:
                result = parser_instance.parse_iso(datetime_string, normalize_whitespace=normalize_ws)
            except (ParserError, ParserMatchError, ValueError, OverflowError, OSError):
                pass  # Expected exceptions

        elif choice == 1:
            # Fuzz DateTimeParser.parse() with format string
            datetime_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))

            # Generate format string
            format_tokens = ['YYYY', 'YY', 'MM', 'M', 'DD', 'D', 'HH', 'H', 'mm', 'm',
                           'ss', 's', 'ZZ', 'Z', 'S', 'W', 'MMMM', 'MMM', 'Do',
                           'dddd', 'ddd', 'a', 'A', 'X', 'x']
            separators = ['-', '/', '.', ':', ' ', 'T', '']

            # Build random format string
            num_tokens = fdp.ConsumeIntInRange(1, 8)
            format_parts = []
            for _ in range(num_tokens):
                if fdp.ConsumeBool():
                    format_parts.append(fdp.PickValueInList(format_tokens))
                if fdp.ConsumeBool():
                    format_parts.append(fdp.PickValueInList(separators))

            fmt = ''.join(format_parts)
            normalize_ws = fdp.ConsumeBool()

            parser_instance = DateTimeParser()
            try:
                result = parser_instance.parse(datetime_string, fmt, normalize_whitespace=normalize_ws)
            except (ParserError, ParserMatchError, ValueError, OverflowError, OSError, KeyError, IndexError):
                pass  # Expected exceptions

        elif choice == 2:
            # Fuzz TzinfoParser.parse()
            tzinfo_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))

            try:
                result = TzinfoParser.parse(tzinfo_string)
            except (ParserError, ValueError, OSError, KeyError):
                pass  # Expected exceptions

        elif choice == 3:
            # Fuzz DateTimeParser.parse() with list of formats
            datetime_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))

            # Generate list of format strings
            format_tokens = ['YYYY-MM-DD', 'YYYY/MM/DD', 'DD-MM-YYYY', 'MM/DD/YYYY',
                           'YYYY-MM-DD HH:mm:ss', 'YYYY-MM-DDTHH:mm:ss',
                           'YYYY-MM-DD HH:mm:ssZ', 'YYYY-MM-DD HH:mm:ssZZ']

            num_formats = fdp.ConsumeIntInRange(1, 5)
            formats = [fdp.PickValueInList(format_tokens) for _ in range(num_formats)]

            parser_instance = DateTimeParser()
            try:
                result = parser_instance.parse(datetime_string, formats)
            except (ParserError, ParserMatchError, ValueError, OverflowError, OSError, KeyError, IndexError):
                pass  # Expected exceptions

    except Exception as e:
        # Catch any unexpected exceptions
        # We want to know about these as they might indicate bugs
        exception_type = type(e).__name__
        # Allow some known safe exception types
        safe_exceptions = [
            'ParserError', 'ParserMatchError', 'ValueError', 'OverflowError',
            'OSError', 'KeyError', 'IndexError', 'AttributeError', 'TypeError',
            'RecursionError', 'MemoryError'
        ]
        if exception_type not in safe_exceptions:
            raise  # Re-raise unexpected exceptions


def main():
    """Main entry point for fuzzing."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
