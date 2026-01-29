#!/usr/bin/env python3
"""
Fuzzing driver for arrow library.
Targets: DateTimeParser.parse_iso(), DateTimeParser.parse(), TzinfoParser.parse()
"""

import atheris
import sys

# Instrument the library before importing
atheris.instrument_imports(["arrow"])

import arrow
from arrow import parser as arrow_parser


@atheris.instrument_func
def fuzz_parse_iso(data):
    """Fuzz DateTimeParser.parse_iso()"""
    try:
        # Try to parse as ISO datetime string
        dt_parser = arrow_parser.DateTimeParser()
        result = dt_parser.parse_iso(data.decode('utf-8', errors='ignore'))
    except (ValueError, TypeError, AttributeError, OverflowError):
        # Expected exceptions for malformed input
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_arrow_get(data):
    """Fuzz arrow.get() - main public API"""
    try:
        # Use FuzzedDataProvider to generate different input types
        fdp = atheris.FuzzedDataProvider(data)

        # Choose test case type
        case_type = fdp.ConsumeIntInRange(0, 3)

        if case_type == 0:
            # Test with ISO string
            iso_string = fdp.ConsumeString(size=200)
            result = arrow.get(iso_string)
        elif case_type == 1:
            # Test with timestamp
            timestamp = fdp.ConsumeFloatInRange(-1e10, 1e10)
            result = arrow.get(timestamp)
        elif case_type == 2:
            # Test with string + format
            datetime_str = fdp.ConsumeString(size=100)
            fmt = fdp.ConsumeString(size=50)
            result = arrow.get(datetime_str, fmt)
        else:
            # Test with timezone string
            tz_str = fdp.ConsumeString(size=50)
            result = arrow.now(tz_str)

    except (ValueError, TypeError, AttributeError, arrow.parser.ParserError):
        # Expected exceptions for invalid input
        return
    except (OverflowError, OSError):
        # OSError can occur for invalid timezone names
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_parse_with_format(data):
    """Fuzz DateTimeParser.parse() with format strings"""
    try:
        fdp = atheris.FuzzedDataProvider(data)

        dt_parser = arrow_parser.DateTimeParser()
        datetime_str = fdp.ConsumeString(size=100)
        format_str = fdp.ConsumeString(size=100)

        result = dt_parser.parse(datetime_str, format_str)

    except (ValueError, TypeError, AttributeError, arrow.parser.ParserError):
        # Expected exceptions
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_tzinfo_parse(data):
    """Fuzz TzinfoParser.parse() for timezone parsing"""
    try:
        tzinfo_parser = arrow_parser.TzinfoParser()
        tz_string = data.decode('utf-8', errors='ignore')
        result = tzinfo_parser.parse(tz_string)

    except (ValueError, TypeError):
        # Expected exceptions for invalid timezone strings
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def test_arrow_fuzzer(data):
    """Main fuzz target dispatcher"""
    if len(data) < 2:
        return

    # Route to different fuzz targets based on first byte
    target = data[0] % 4
    remaining_data = data[1:]

    if target == 0:
        fuzz_parse_iso(remaining_data)
    elif target == 1:
        fuzz_arrow_get(remaining_data)
    elif target == 2:
        fuzz_parse_with_format(remaining_data)
    else:
        fuzz_tzinfo_parse(remaining_data)


# Setup and run fuzzer
atheris.Setup(sys.argv, test_arrow_fuzzer)
atheris.Fuzz()
