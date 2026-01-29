"""
Fuzz driver for Arrow library - Date/time parsing and manipulation.
Coverage-guided fuzzing using atheris/pythonfuzz pattern.
"""

import sys
import datetime
from typing import Any, List, Optional, Tuple, Union

# Arrow module path adjustment
sys.path.insert(0, '/app/arrow')

import arrow
from arrow import Arrow
from arrow.parser import ParserError


def validate_utf8(data: bytes) -> bool:
    """Check if data is valid UTF-8."""
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def safe_unicode_decode(data: bytes) -> str:
    """Safely decode bytes to string."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('utf-8', errors='replace')


def fuzz_arrow_get(data: bytes) -> None:
    """Fuzz arrow.get() with various input formats."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        # Test basic string parsing
        result = arrow.get(input_str)
        # Use the result to ensure coverage
        _ = result.timestamp
        _ = result.format()
    except (ParserError, ValueError, OverflowError, TypeError):
        pass

    # Test with locale
    try:
        result = arrow.get(input_str, locale='en-us')
        _ = result.isoformat()
    except (ParserError, ValueError, LookupError):
        pass


def fuzz_arrow_factory(data: bytes) -> None:
    """Fuzz ArrowFactory methods."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)
    factory = arrow.ArrowFactory()

    try:
        # Test get with timestamp
        result = factory.get(int(input_str) if input_str.isdigit() else 0)
        _ = result.int_timestamp
    except (ValueError, OverflowError, TypeError):
        pass

    try:
        # Test get with tuple
        result = factory.get((2023, 1, 1))
        _ = result.day
    except (ValueError, TypeError):
        pass


def fuzz_arrow_methods(data: bytes) -> None:
    """Fuzz Arrow object methods."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)
    arw = arrow.utcnow()

    try:
        # Test format
        _ = arw.format()
        _ = arw.format('YYYY-MM-DD')
        _ = arw.format('HH:mm:ss')
        _ = arw.format('MMMM DD, YYYY')
    except (ValueError, KeyError):
        pass

    try:
        # Test shift
        shifted = arw.shift(hours=1)
        _ = shifted.hour
    except (ValueError, TypeError):
        pass

    try:
        # Test replace
        replaced = arw.replace(year=2024)
        _ = replaced.year
    except (ValueError, TypeError):
        pass

    try:
        # Test span
        start, end = arw.span('day')
        _ = start.timestamp
        _ = end.timestamp
    except (ValueError, TypeError):
        pass


def fuzz_arrow_dehumanize(data: bytes) -> None:
    """Fuzz dehumanize parsing."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    try:
        # Test common phrases
        phrases = [
            f'{input_str} ago',
            f'in {input_str}',
            f'{input_str} from now',
        ]
        for phrase in phrases:
            try:
                result = arrow.utcnow().dehumanize(phrase)
            except (ParserError, ValueError, TypeError):
                pass
    except (ParserError, ValueError):
        pass


def fuzz_edge_cases(data: bytes) -> None:
    """Test edge cases and boundary conditions."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)

    # Test various string formats
    formats = [
        input_str,
        f'{input_str}T00:00:00',
        f'{input_str} 00:00:00',
        f'2023-01-01 {input_str}',
        input_str[:8] if len(input_str) >= 8 else input_str,
    ]

    for fmt in formats:
        try:
            result = arrow.get(fmt)
            _ = result.timestamp
        except (ParserError, ValueError, OverflowError, TypeError):
            pass


def fuzz_timestamp_edge_cases(data: bytes) -> None:
    """Test timestamp edge cases."""
    try:
        # Parse as integer if possible
        ts = int.from_bytes(data[:8], 'big', signed=True)
        result = arrow.get(ts)
        _ = result.timestamp
    except (ValueError, OverflowError, TypeError, ParserError):
        pass

    try:
        # Parse as float from struct
        import struct
        ts = struct.unpack('>d', data[:8])[0]
        result = arrow.get(ts)
        _ = result.timestamp
    except (ValueError, OverflowError, TypeError, ParserError, struct.error):
        pass


def fuzz_format_strings(data: bytes) -> None:
    """Test various format strings."""
    if not validate_utf8(data):
        return

    input_str = safe_unicode_decode(data)
    arw = arrow.utcnow()

    format_patterns = [
        input_str,
        'YYYY-MM-DD',
        'HH:mm:ss',
        'MMMM DD YYYY',
        'ddd MMM DD HH:mm:ss YYYY',
        'X',
        'x',
        input_str[:10] if len(input_str) > 10 else input_str,
    ]

    for fmt in format_patterns:
        try:
            _ = arw.format(fmt)
        except (ValueError, KeyError, TypeError):
            pass


def main():
    """Main entry point for fuzzing."""
    import os

    # Get input from stdin (LibFuzzer/AFL style) or use provided data
    if len(sys.argv) > 1:
        # Read from file (AFL/LibFuzzer queue)
        with open(sys.argv[1], 'rb') as f:
            data = f.read()
    else:
        # Read from stdin
        data = sys.stdin.buffer.read()

    if not data:
        return

    # Run all fuzz targets
    fuzz_arrow_get(data)
    fuzz_arrow_factory(data)
    fuzz_arrow_methods(data)
    fuzz_arrow_dehumanize(data)
    fuzz_edge_cases(data)
    fuzz_timestamp_edge_cases(data)
    fuzz_format_strings(data)


if __name__ == '__main__':
    main()
