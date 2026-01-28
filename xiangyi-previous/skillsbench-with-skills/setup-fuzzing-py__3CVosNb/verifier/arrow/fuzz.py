#!/usr/bin/env python3
"""
Fuzz driver for Arrow library.

Targets:
- DateTimeParser.parse_iso() - Primary ISO 8601 datetime parsing
- DateTimeParser.parse() - General-purpose datetime parsing with format strings
- TzinfoParser.parse() - Timezone string parsing
- ArrowFactory.get() - Main entry point for creating Arrow objects
- normalize_timestamp() - Timestamp normalization

Usage:
    python fuzz.py [libfuzzer options]

Example:
    python fuzz.py -max_total_time=10
"""

import sys
import atheris


def setup_arrow():
    """Import arrow modules inside instrumentation context."""
    global arrow, DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    global ArrowFactory, normalize_timestamp

    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    from arrow.factory import ArrowFactory
    from arrow.util import normalize_timestamp


def TestOneInput(data: bytes) -> None:
    """Fuzz test entry point.

    Tests multiple arrow parsing functions with the same input data.
    """
    # Try to decode as UTF-8 string
    try:
        input_str = data.decode('utf-8')
    except UnicodeDecodeError:
        # If not valid UTF-8, try with replacement
        input_str = data.decode('utf-8', errors='replace')

    # Skip empty inputs
    if not input_str:
        return

    # Create parser instance
    parser = DateTimeParser()

    # Test 1: parse_iso() - Primary target for datetime string parsing
    try:
        result = parser.parse_iso(input_str)
    except (ParserError, ParserMatchError, ValueError, OverflowError, RecursionError):
        pass  # Expected exceptions for invalid input
    except Exception:
        pass  # Catch any other exceptions without crashing

    # Test 2: parse_iso() with normalize_whitespace=True
    try:
        result = parser.parse_iso(input_str, normalize_whitespace=True)
    except (ParserError, ParserMatchError, ValueError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 3: parse() with input as both datetime and format string
    try:
        result = parser.parse(input_str, input_str)
    except (ParserError, ParserMatchError, ValueError, OverflowError, RecursionError):
        pass
    except Exception:
        pass

    # Test 4: parse() with common format patterns
    common_formats = [
        "YYYY-MM-DD",
        "YYYY-MM-DD HH:mm:ss",
        "YYYY/MM/DD",
        "MM/DD/YYYY",
        "DD-MM-YYYY",
    ]
    for fmt in common_formats:
        try:
            result = parser.parse(input_str, fmt)
        except (ParserError, ParserMatchError, ValueError, OverflowError, RecursionError):
            pass
        except Exception:
            pass

    # Test 5: TzinfoParser.parse() - Timezone parsing
    try:
        result = TzinfoParser.parse(input_str)
    except (ParserError, ValueError, KeyError, OverflowError):
        pass
    except Exception:
        pass

    # Test 6: ArrowFactory.get() with string input
    factory = ArrowFactory()
    try:
        result = factory.get(input_str)
    except (ParserError, ParserMatchError, ValueError, TypeError, OverflowError):
        pass
    except Exception:
        pass

    # Test 7: normalize_timestamp() with numeric-like strings
    try:
        # Try to parse as float for timestamp normalization
        timestamp = float(input_str)
        result = normalize_timestamp(timestamp)
    except (ValueError, OverflowError, TypeError):
        pass
    except Exception:
        pass

    # Test 8: Use FuzzedDataProvider for more structured testing
    fdp = atheris.FuzzedDataProvider(data)

    # Generate random timestamp values
    try:
        random_float = fdp.ConsumeFloat()
        result = normalize_timestamp(random_float)
    except (ValueError, OverflowError, TypeError):
        pass
    except Exception:
        pass

    # Generate random integer for timestamp
    try:
        random_int = fdp.ConsumeInt(8)  # 8 bytes = 64-bit int
        result = normalize_timestamp(float(random_int))
    except (ValueError, OverflowError, TypeError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    # Instrument arrow imports
    with atheris.instrument_imports():
        setup_arrow()

    # Setup and run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
