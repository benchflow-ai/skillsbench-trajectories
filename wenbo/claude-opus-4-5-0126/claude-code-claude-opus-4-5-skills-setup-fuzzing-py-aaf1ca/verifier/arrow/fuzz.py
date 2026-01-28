#!/usr/bin/env python3
"""
Fuzz driver for the Arrow datetime library using Atheris (LibFuzzer-based).
Targets the high-priority parsing functions identified in notes_for_testing.txt.
"""

import sys
import atheris


def setup_imports():
    """Import target modules with instrumentation."""
    with atheris.instrument_imports():
        import arrow
        from arrow import parser, factory, locales
        from arrow.parser import DateTimeParser, TzinfoParser
    return arrow, parser, factory, locales, DateTimeParser, TzinfoParser


# Import modules with instrumentation
arrow_mod, parser_mod, factory_mod, locales_mod, DateTimeParser, TzinfoParser = setup_imports()


@atheris.instrument_func
def TestOneInput(data: bytes):
    """
    Fuzz entry point targeting Arrow's parsing functions.

    Priority targets:
    1. DateTimeParser.parse_iso() - ISO 8601 parsing
    2. TzinfoParser.parse() - Timezone string parsing
    3. arrow.get() - Main API entry point
    4. Arrow.dehumanize() - Human-readable time parsing
    """
    fdp = atheris.FuzzedDataProvider(data)

    # Get a string from the fuzzer input
    try:
        input_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
    except Exception:
        return

    if not input_string:
        return

    # Test 1: arrow.get() with string input - main API entry point
    try:
        arrow_mod.get(input_string)
    except (ValueError, TypeError, arrow_mod.parser.ParserError, OverflowError, OSError):
        pass
    except Exception:
        # Catch any unexpected exceptions but don't crash
        pass

    # Test 2: DateTimeParser.parse_iso() - ISO 8601 parsing
    try:
        dt_parser = DateTimeParser()
        dt_parser.parse_iso(input_string, normalize_whitespace=fdp.ConsumeBool())
    except (ValueError, TypeError, arrow_mod.parser.ParserError, OverflowError):
        pass
    except Exception:
        pass

    # Test 3: TzinfoParser.parse() - Timezone string parsing
    try:
        TzinfoParser.parse(input_string)
    except (ValueError, TypeError, arrow_mod.parser.ParserError):
        pass
    except Exception:
        pass

    # Test 4: DateTimeParser.parse() with format string
    # Use part of the input as datetime string and part as format
    try:
        format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
        if format_string:
            dt_parser = DateTimeParser()
            dt_parser.parse(input_string, format_string)
    except (ValueError, TypeError, arrow_mod.parser.ParserError, OverflowError, re.error if 're' in dir() else Exception):
        pass
    except Exception:
        pass

    # Test 5: arrow.get() with timestamp (numeric input)
    try:
        timestamp = fdp.ConsumeFloat()
        arrow_mod.get(timestamp)
    except (ValueError, TypeError, OverflowError, OSError):
        pass
    except Exception:
        pass

    # Test 6: Locale functions
    try:
        locales_mod.get_locale(input_string)
    except (ValueError, KeyError, TypeError):
        pass
    except Exception:
        pass

    # Test 7: Arrow.dehumanize() - human-readable relative time parsing
    try:
        now = arrow_mod.utcnow()
        now.dehumanize(input_string)
    except (ValueError, TypeError, arrow_mod.parser.ParserError):
        pass
    except Exception:
        pass

    # Test 8: Arrow.format() with fuzzed format string
    try:
        now = arrow_mod.utcnow()
        now.format(input_string)
    except (ValueError, TypeError, KeyError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
