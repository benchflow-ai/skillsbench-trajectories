"""Fuzz driver for Arrow datetime library."""
import atheris
import sys
from typing import Union

try:
    import arrow
except ImportError:
    # Will be installed during virtual env setup
    pass


@atheris.instrument_func
def test_one(data: bytes) -> None:
    """Main fuzz target for Arrow library."""
    if len(data) < 1:
        return

    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Parse input as UTF-8 string for datetime parsing
        input_str = fdp.ConsumeUnicodeString(500)

        # Test 1: Parse ISO 8601 strings
        if len(input_str) > 0:
            try:
                result = arrow.get(input_str)
            except (arrow.parser.ParserError, ValueError, TypeError):
                pass

        # Test 2: Create Arrow objects with various inputs
        choice = fdp.ConsumeIntInRange(0, 3)

        if choice == 0 and len(input_str) > 0:
            # Test format string handling
            try:
                arrow.now().format(input_str)
            except (ValueError, arrow.parser.ParserError, TypeError):
                pass

        elif choice == 1:
            # Test with timestamps
            timestamp = fdp.ConsumeIntInRange(-2147483648, 2147483647)
            try:
                arrow.get(timestamp)
            except (ValueError, OSError, OverflowError):
                pass

        elif choice == 2:
            # Test replace() with random values
            year = fdp.ConsumeIntInRange(1900, 2100)
            month = fdp.ConsumeIntInRange(1, 12)
            day = fdp.ConsumeIntInRange(1, 28)
            try:
                arrow.now().replace(year=year, month=month, day=day)
            except (ValueError, arrow.parser.ParserError):
                pass

        elif choice == 3:
            # Test shift operations
            days = fdp.ConsumeIntInRange(-1000, 1000)
            hours = fdp.ConsumeIntInRange(-24, 24)
            try:
                arrow.now().shift(days=days, hours=hours)
            except (ValueError, OverflowError):
                pass

    except (
        ValueError,
        TypeError,
        AttributeError,
        arrow.parser.ParserError,
        OverflowError,
        OSError,
    ):
        # Expected exceptions during fuzzing
        return
    except Exception as e:
        # Log unexpected exceptions
        raise


def main() -> None:
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
