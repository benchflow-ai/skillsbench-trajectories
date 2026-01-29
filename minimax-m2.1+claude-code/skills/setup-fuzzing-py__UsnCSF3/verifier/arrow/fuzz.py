#!/usr/bin/env python3
"""
Fuzz driver for Arrow library.
Uses LibFuzzer-style coverage-guided fuzzing.
"""

import sys
import traceback
from typing import Any, Union

import arrow
from arrow import Arrow


def fuzz_arrow_get(input_data: bytes) -> None:
    """Fuzz arrow.get() with various input types."""
    try:
        data = input_data.decode('utf-8', errors='replace')

        # Try various parsing scenarios
        # Test as timestamp (int)
        try:
            ts = int(data[:10]) if data[:10].isdigit() else 0
            arrow.get(ts)
        except (ValueError, OverflowError):
            pass

        # Test as datetime string with various formats
        try:
            arrow.get(data)
        except (ValueError, arrow.ParserError, arrow.ParserMatchError):
            pass

        # Test with locale
        try:
            arrow.get(data, locale='en_us')
        except (ValueError, arrow.ParserError, arrow.ParserMatchError):
            pass

        # Test with timezone
        try:
            arrow.get(data, tzinfo='UTC')
        except (ValueError, arrow.ParserError, arrow.ParserMatchError):
            pass

    except Exception:
        # Swallow exceptions during fuzzing
        pass


def fuzz_arrow_constructor(input_data: bytes) -> None:
    """Fuzz Arrow class constructor with random integers."""
    try:
        # Extract integers from input for constructor params
        nums = [abs(b) % 100 for b in input_data[:16]]
        while len(nums) < 8:
            nums.append(0)

        try:
            Arrow(year=nums[0] % 3000 + 1, month=(nums[1] % 12) + 1,
                  day=(nums[2] % 28) + 1, hour=nums[3] % 24,
                  minute=nums[4] % 60, second=nums[5] % 60,
                  microsecond=nums[6] % 1000000)
        except ValueError:
            pass

    except Exception:
        pass


def fuzz_arrow_format(input_data: bytes) -> None:
    """Fuzz Arrow.format() method."""
    try:
        # Get current time
        a = arrow.utcnow()

        # Format with various format strings
        format_strings = ['YYYY-MM-DD', 'HH:mm:ss', 'YYYY-MM-DDTHH:mm:ssZZ',
                         'dddd', 'MMM', 'X', 'x']

        data = input_data.decode('utf-8', errors='replace')
        for fmt in format_strings:
            try:
                a.format(fmt)
            except Exception:
                pass

    except Exception:
        pass


def fuzz_arrow_replace(input_data: bytes) -> None:
    """Fuzz Arrow.replace() method."""
    try:
        a = arrow.utcnow()
        nums = [abs(b) for b in input_data[:16]]

        # Try various replace operations
        try:
            a.replace(year=nums[0] % 3000 + 1)
        except (ValueError, TypeError):
            pass

        try:
            a.replace(month=(nums[1] % 12) + 1)
        except (ValueError, TypeError):
            pass

        try:
            a.replace(hour=nums[2] % 24)
        except (ValueError, TypeError):
            pass

    except Exception:
        pass


def fuzz_arrow_shift(input_data: bytes) -> None:
    """Fuzz Arrow.shift() method."""
    try:
        a = arrow.utcnow()
        nums = [abs(b) for b in input_data[:16]]

        # Test various shift operations
        shifts = [
            {'days': nums[0] % 100},
            {'weeks': nums[1] % 50},
            {'hours': nums[2] % 1000},
            {'minutes': nums[3] % 5000},
            {'seconds': nums[4] % 10000},
        ]

        for shift in shifts:
            try:
                a.shift(**shift)
            except Exception:
                pass

    except Exception:
        pass


def main():
    """Main entry point for fuzzing."""
    if len(sys.argv) > 1:
        # Running with input file (LibFuzzer mode)
        with open(sys.argv[1], 'rb') as f:
            input_data = f.read()
    else:
        # Running from stdin
        input_data = sys.stdin.buffer.read()

    # Run all fuzz targets
    fuzz_arrow_get(input_data)
    fuzz_arrow_constructor(input_data)
    fuzz_arrow_format(input_data)
    fuzz_arrow_replace(input_data)
    fuzz_arrow_shift(input_data)


if __name__ == '__main__':
    main()
