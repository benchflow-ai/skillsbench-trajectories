#!/usr/bin/env python3
"""
Fuzz driver for Arrow datetime library.

Targets: DateTimeParser.parse_iso() and DateTimeParser.parse()
These are high-value parsing functions accepting untrusted string input.
"""

import sys
import atheris

# Import arrow modules with instrumentation
with atheris.instrument_imports():
    from arrow.parser import DateTimeParser, ParserError, ParserMatchError


def TestOneInput(data):
    """
    Fuzz target for arrow datetime parsing.

    This fuzzer tests:
    1. parse_iso() - ISO 8601-like datetime parsing
    2. parse() with common format strings

    Expected behavior:
    - Valid datetime strings should parse successfully
    - Invalid strings should raise ParserError or ParserMatchError
    - No crashes, hangs, or uncaught exceptions
    """
    if len(data) == 0:
        return

    # Decode fuzzer input to string (ignore invalid UTF-8)
    try:
        input_str = data.decode('utf-8', errors='ignore')
    except Exception:
        return

    # Skip if empty after decoding
    if not input_str or len(input_str) > 10000:
        # Avoid extremely long strings that cause timeouts
        return

    # Create parser instance
    parser = DateTimeParser()

    # Test 1: Fuzz parse_iso()
    try:
        parser.parse_iso(input_str)
    except (ParserError, ParserMatchError):
        # These are expected exceptions for invalid input
        pass
    except ValueError:
        # Some edge cases may raise ValueError (e.g., invalid dates)
        pass
    except OverflowError:
        # Extreme timestamp values may overflow
        pass
    except Exception as e:
        # Any other exception is suspicious - let atheris report it
        raise

    # Test 2: Fuzz parse() with common format strings if input has delimiter
    if len(input_str) >= 3 and '|||' in input_str:
        parts = input_str.split('|||', 1)
        if len(parts) == 2:
            datetime_str, format_str = parts

            # Limit format string length to avoid ReDoS
            if len(format_str) > 200:
                return

            try:
                parser.parse(datetime_str, format_str)
            except (ParserError, ParserMatchError):
                # Expected for mismatched datetime/format
                pass
            except ValueError:
                # Invalid dates
                pass
            except OverflowError:
                # Extreme values
                pass
            except Exception as e:
                # Any other exception is suspicious
                raise


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
