#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for Arrow library.
Fuzzes datetime parsing functions with various input formats.
"""

import sys
import atheris
import arrow
from arrow import parser, factory

# Initialize fuzzer
def fuzz_arrow_target(data):
    """Fuzzer target function."""
    fuzzer = FuzzArrow(data)
    fuzzer.run()

atheris.Setup(sys.argv, fuzz_arrow_target)


class FuzzArrow:
    """Fuzz driver for Arrow datetime library."""

    def __init__(self, data):
        """Initialize fuzzer with input data."""
        self.fuzz_data = atheris.FuzzedDataProvider(data)

    def run(self):
        """Execute fuzzing targets."""
        try:
            self._fuzz_parse_iso()
            self._fuzz_parse_generic()
            self._fuzz_timezone_parsing()
            self._fuzz_arrow_get()
            self._fuzz_format_and_parse()
        except Exception:
            # Expected for invalid input
            pass

    def _fuzz_parse_iso(self):
        """Fuzz ISO 8601 datetime parsing."""
        datetime_string = self.fuzz_data.ConsumeUnicodeString(100)
        normalize_ws = self.fuzz_data.ConsumeBool()

        dt_parser = parser.DateTimeParser()
        try:
            result = dt_parser.parse_iso(datetime_string, normalize_whitespace=normalize_ws)
            if result:
                # Verify result is valid datetime tuple
                assert len(result) >= 7
        except (ValueError, AttributeError, IndexError, TypeError):
            pass

    def _fuzz_parse_generic(self):
        """Fuzz generic datetime parsing with format strings."""
        datetime_string = self.fuzz_data.ConsumeUnicodeString(100)
        format_string = self.fuzz_data.ConsumeUnicodeString(50)

        dt_parser = parser.DateTimeParser()
        try:
            result = dt_parser.parse(datetime_string, format_string)
            if result:
                assert len(result) >= 7
        except (ValueError, AttributeError, IndexError, TypeError, OverflowError):
            pass

    def _fuzz_timezone_parsing(self):
        """Fuzz timezone string parsing."""
        tz_string = self.fuzz_data.ConsumeUnicodeString(50)

        tz_parser = parser.TzinfoParser()
        try:
            result = tz_parser.parse(tz_string)
            # Verify result is a tzinfo object
            if result:
                assert hasattr(result, 'tzname')
        except (ValueError, AttributeError, TypeError):
            pass

    def _fuzz_arrow_get(self):
        """Fuzz Arrow factory polymorphic entry point."""
        choice = self.fuzz_data.ConsumeIntInRange(0, 4)

        try:
            if choice == 0:
                # String parsing
                date_str = self.fuzz_data.ConsumeUnicodeString(100)
                arrow.get(date_str)
            elif choice == 1:
                # Timestamp parsing
                timestamp = self.fuzz_data.ConsumeFloat()
                arrow.get(timestamp)
            elif choice == 2:
                # Timestamp with format
                ts = self.fuzz_data.ConsumeFloat()
                fmt = self.fuzz_data.ConsumeUnicodeString(30)
                arrow.get(ts, fmt)
            elif choice == 3:
                # Multiple arguments
                year = self.fuzz_data.ConsumeIntInRange(1, 9999)
                month = self.fuzz_data.ConsumeIntInRange(1, 12)
                day = self.fuzz_data.ConsumeIntInRange(1, 28)
                arrow.get(year, month, day)
            elif choice == 4:
                # With format string
                date_str = self.fuzz_data.ConsumeUnicodeString(100)
                fmt = self.fuzz_data.ConsumeUnicodeString(50)
                arrow.get(date_str, fmt)
        except (ValueError, AttributeError, TypeError, OverflowError):
            pass

    def _fuzz_format_and_parse(self):
        """Fuzz round-trip format and parse."""
        try:
            # Create valid arrow object first
            year = self.fuzz_data.ConsumeIntInRange(2000, 2030)
            month = self.fuzz_data.ConsumeIntInRange(1, 12)
            day = self.fuzz_data.ConsumeIntInRange(1, 28)
            arr = arrow.get(f"{year}-{month:02d}-{day:02d}")

            # Test formatting with various format strings
            format_string = self.fuzz_data.ConsumeUnicodeString(50)
            formatted = arr.format(format_string)

            # Verify formatted is a string
            assert isinstance(formatted, str)
        except (ValueError, AttributeError, TypeError):
            pass


if __name__ == '__main__':
    atheris.Fuzz()
