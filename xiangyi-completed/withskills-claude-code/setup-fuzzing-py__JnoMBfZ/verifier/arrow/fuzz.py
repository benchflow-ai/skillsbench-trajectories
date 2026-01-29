#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for the Arrow datetime library.

This fuzzer targets the following functions:
1. DateTimeParser.parse_iso() - ISO 8601 datetime string parsing
2. DateTimeParser.parse() - Custom format string parsing
3. TzinfoParser.parse() - Timezone string parsing
4. arrow.get() - Main factory method for parsing various inputs

Usage:
    python fuzz.py                    # Run fuzzer indefinitely
    python fuzz.py -max_total_time=10 # Run for 10 seconds
    python fuzz.py corpus/            # Run with corpus directory
"""

import sys
import atheris


def setup_module():
    """Import and instrument the arrow module."""
    with atheris.instrument_imports():
        import arrow
        from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    return arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError


# Import modules with instrumentation
arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError = setup_module()


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Fuzz test entry point for arrow datetime parsing.

    This function tests multiple parsing functions with the fuzzed input.
    """
    # Need at least 1 byte for the mode selector
    if len(data) < 2:
        return

    # Use first byte to select which function to fuzz
    mode = data[0] % 5

    try:
        # Decode the rest as UTF-8 string, replacing invalid chars
        input_str = data[1:].decode('utf-8', errors='replace')
    except Exception:
        return

    # Skip empty strings
    if not input_str:
        return

    try:
        if mode == 0:
            # Fuzz DateTimeParser.parse_iso()
            parser = DateTimeParser()
            parser.parse_iso(input_str)

        elif mode == 1:
            # Fuzz DateTimeParser.parse_iso() with normalize_whitespace=True
            parser = DateTimeParser()
            parser.parse_iso(input_str, normalize_whitespace=True)

        elif mode == 2:
            # Fuzz DateTimeParser.parse() with a simple format string
            # Use part of input as format string
            if len(input_str) > 10:
                fmt_str = input_str[:10]
                datetime_str = input_str[10:]
                parser = DateTimeParser()
                parser.parse(datetime_str, fmt_str)

        elif mode == 3:
            # Fuzz TzinfoParser.parse()
            TzinfoParser.parse(input_str)

        elif mode == 4:
            # Fuzz arrow.get() with string input
            arrow.get(input_str)

    except (ParserError, ParserMatchError):
        # Expected exceptions for invalid input
        pass
    except ValueError:
        # Expected for invalid values
        pass
    except OverflowError:
        # Expected for extreme numeric values
        pass
    except re.error:
        # Expected for invalid regex patterns in format strings
        pass
    except KeyError:
        # Can happen with invalid locale/timezone lookups
        pass
    except TypeError:
        # Can happen with type mismatches
        pass
    except RecursionError:
        # Should not happen - indicates potential DoS
        raise
    except MemoryError:
        # Should not happen - indicates potential DoS
        raise
    except AttributeError:
        # Should not happen - indicates bug
        raise
    except IndexError:
        # Should not happen - indicates bug
        raise


# Import re for exception handling
import re


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
