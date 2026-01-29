#!/usr/bin/env python3
"""
Fuzz driver for Arrow library using Atheris/LibFuzzer.

Targets:
- DateTimeParser.parse_iso: Primary ISO 8601 datetime parsing
- DateTimeParser.parse: Custom format datetime parsing
- TzinfoParser.parse: Timezone string parsing
- normalize_timestamp: Timestamp normalization
- iso_to_gregorian: ISO week date conversion
"""

import sys
import atheris


def setup_arrow():
    """Import arrow modules inside instrumentation context."""
    global DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    global normalize_timestamp, iso_to_gregorian

    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError
    from arrow.util import normalize_timestamp, iso_to_gregorian


# Acceptable exceptions that indicate proper error handling
ACCEPTABLE_EXCEPTIONS = (
    "ParserError",
    "ParserMatchError",
    "ValueError",
    "OverflowError",
    "TypeError",
    "re.error",
)


def is_acceptable_exception(e: Exception) -> bool:
    """Check if exception is expected/acceptable."""
    exc_name = type(e).__name__
    return any(acceptable in exc_name for acceptable in ACCEPTABLE_EXCEPTIONS)


def fuzz_parse_iso(data: bytes) -> None:
    """Fuzz DateTimeParser.parse_iso with arbitrary strings."""
    try:
        datetime_string = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return

    parser = DateTimeParser()

    # Test parse_iso
    try:
        parser.parse_iso(datetime_string)
    except Exception as e:
        if not is_acceptable_exception(e):
            raise

    # Test with normalize_whitespace=True
    try:
        parser.parse_iso(datetime_string, normalize_whitespace=True)
    except Exception as e:
        if not is_acceptable_exception(e):
            raise


def fuzz_parse_with_format(data: bytes) -> None:
    """Fuzz DateTimeParser.parse with datetime string and format."""
    fdp = atheris.FuzzedDataProvider(data)

    datetime_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
    format_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))

    if not datetime_string or not format_string:
        return

    parser = DateTimeParser()

    try:
        parser.parse(datetime_string, format_string)
    except Exception as e:
        if not is_acceptable_exception(e):
            raise


def fuzz_tzinfo_parse(data: bytes) -> None:
    """Fuzz TzinfoParser.parse with timezone strings."""
    try:
        tz_string = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return

    try:
        TzinfoParser.parse(tz_string)
    except Exception as e:
        if not is_acceptable_exception(e):
            raise


def fuzz_normalize_timestamp(data: bytes) -> None:
    """Fuzz normalize_timestamp with various numeric values."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test with regular float
    try:
        timestamp = fdp.ConsumeFloat()
        normalize_timestamp(timestamp)
    except Exception as e:
        if not is_acceptable_exception(e):
            raise

    # Test with integer
    try:
        timestamp = fdp.ConsumeInt(8)
        normalize_timestamp(float(timestamp))
    except Exception as e:
        if not is_acceptable_exception(e):
            raise


def fuzz_iso_to_gregorian(data: bytes) -> None:
    """Fuzz iso_to_gregorian with various integer triplets."""
    fdp = atheris.FuzzedDataProvider(data)

    iso_year = fdp.ConsumeIntInRange(-10000, 10000)
    iso_week = fdp.ConsumeIntInRange(-100, 100)
    iso_day = fdp.ConsumeIntInRange(-100, 100)

    try:
        iso_to_gregorian(iso_year, iso_week, iso_day)
    except Exception as e:
        if not is_acceptable_exception(e):
            raise


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Main fuzzer entry point - tests all targets."""
    if len(data) < 2:
        return

    # Use first byte to select which target to fuzz
    selector = data[0] % 5
    payload = data[1:]

    if selector == 0:
        fuzz_parse_iso(payload)
    elif selector == 1:
        fuzz_parse_with_format(payload)
    elif selector == 2:
        fuzz_tzinfo_parse(payload)
    elif selector == 3:
        fuzz_normalize_timestamp(payload)
    elif selector == 4:
        fuzz_iso_to_gregorian(payload)


def main():
    # Instrument imports for coverage
    with atheris.instrument_imports():
        setup_arrow()

    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
