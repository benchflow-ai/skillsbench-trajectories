#!/usr/bin/env python3
"""
Coverage-guided fuzzing for Arrow library using atheris (LibFuzzer compatible).

Targets:
- DateTimeParser.parse_iso(): ISO 8601 datetime string parsing
- DateTimeParser.parse(): Custom format datetime parsing
- TzinfoParser.parse(): Timezone string parsing
- Arrow.dehumanize(): Human-readable time string parsing
- arrow.get(): Flexible Arrow object construction
"""

import sys
import atheris


def setup_arrow():
    """Import arrow and related modules."""
    global arrow, DateTimeParser, TzinfoParser
    import arrow as arrow_module
    from arrow.parser import DateTimeParser as DTP, TzinfoParser as TZP
    arrow = arrow_module
    DateTimeParser = DTP
    TzinfoParser = TZP


def fuzz_parse_iso(data: bytes):
    """Fuzz DateTimeParser.parse_iso() with arbitrary strings."""
    try:
        string = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    parser = DateTimeParser()
    try:
        parser.parse_iso(string)
    except (arrow.parser.ParserError, ValueError, OverflowError):
        pass


def fuzz_parse_with_format(data: bytes):
    """Fuzz DateTimeParser.parse() with both datetime string and format."""
    try:
        # Split data into datetime string and format using null byte separator
        if b'\x00' not in data:
            return
        parts = data.split(b'\x00', 1)
        datetime_str = parts[0].decode('utf-8')
        fmt = parts[1].decode('utf-8')
    except (UnicodeDecodeError, IndexError):
        return

    parser = DateTimeParser()
    try:
        parser.parse(datetime_str, fmt)
    except (arrow.parser.ParserError, ValueError, OverflowError, KeyError, AttributeError):
        pass
    except Exception:
        # Catch regex errors and other parsing issues
        pass


def fuzz_timezone_parse(data: bytes):
    """Fuzz TzinfoParser.parse() with timezone strings."""
    try:
        string = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        TzinfoParser.parse(string)
    except (arrow.parser.ParserError, ValueError, KeyError):
        pass


def fuzz_dehumanize(data: bytes):
    """Fuzz Arrow.dehumanize() with human-readable time strings."""
    try:
        string = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        arw = arrow.utcnow()
        arw.dehumanize(string)
    except (ValueError, AttributeError, TypeError):
        pass


def fuzz_arrow_get(data: bytes):
    """Fuzz arrow.get() with arbitrary strings."""
    try:
        string = data.decode('utf-8')
    except UnicodeDecodeError:
        return

    try:
        arrow.get(string)
    except (arrow.parser.ParserError, TypeError, ValueError, OverflowError):
        pass


def TestOneInput(data: bytes):
    """Main fuzzing entry point - calls all fuzz targets."""
    if len(data) < 1:
        return

    # Use first byte to select target
    selector = data[0] % 5
    payload = data[1:]

    if selector == 0:
        fuzz_parse_iso(payload)
    elif selector == 1:
        fuzz_parse_with_format(payload)
    elif selector == 2:
        fuzz_timezone_parse(payload)
    elif selector == 3:
        fuzz_dehumanize(payload)
    else:
        fuzz_arrow_get(payload)


def main():
    """Main entry point for the fuzzer."""
    setup_arrow()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
