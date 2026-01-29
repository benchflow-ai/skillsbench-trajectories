#!/usr/bin/env python3
"""
Coverage-guided fuzzer for Arrow library using Atheris (LibFuzzer).
Targets date/time parsing functions which are most likely to have edge cases.
"""

import sys
import atheris

# Enable coverage instrumentation before importing target modules
with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser


def TestOneInput(data):
    """Fuzz target for arrow library."""

    # Need at least some bytes to work with
    if len(data) < 1:
        return

    try:
        input_str = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not input_str:
        return

    # Test 1: arrow.get() with string input - main entry point
    try:
        arrow.get(input_str)
    except (ValueError, TypeError, arrow.parser.ParserError,
            arrow.parser.ParserMatchError, OverflowError, OSError):
        pass
    except Exception:
        pass

    # Test 2: DateTimeParser.parse_iso() - ISO format parsing
    try:
        parser = DateTimeParser()
        parser.parse_iso(input_str)
    except (ValueError, TypeError, arrow.parser.ParserError,
            arrow.parser.ParserMatchError, OverflowError):
        pass
    except Exception:
        pass

    # Test 3: TzinfoParser.parse() - timezone parsing
    try:
        tz_parser = TzinfoParser()
        tz_parser.parse(input_str)
    except (ValueError, TypeError, arrow.parser.ParserError,
            arrow.parser.ParserMatchError):
        pass
    except Exception:
        pass

    # Test 4: arrow.get() with format string (use input as both date and format)
    if len(input_str) > 2:
        mid = len(input_str) // 2
        date_part = input_str[:mid]
        format_part = input_str[mid:]
        try:
            arrow.get(date_part, format_part)
        except (ValueError, TypeError, arrow.parser.ParserError,
                arrow.parser.ParserMatchError, OverflowError):
            pass
        except Exception:
            pass

    # Test 5: Arrow.dehumanize() - natural language parsing
    try:
        now = arrow.now()
        now.dehumanize(input_str)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass


def main():
    # Run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
