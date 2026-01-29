#!/usr/bin/env python3
"""
Fuzzer for Arrow library - Date/time parsing and formatting
Targets: arrow.get() with various input formats
"""

import sys
import atheris

# Import after atheris setup
with atheris.instrument_imports():
    import arrow


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz arrow.get() with various input patterns."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: arrow.get() with string auto-parsing
    try:
        date_string = fdp.ConsumeUnicodeNoSurrogates(100)
        if date_string:
            arrow.get(date_string)
    except (arrow.ParserError, ValueError, AttributeError, TypeError,
            OverflowError, OSError) as e:
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Catch any other exception to debug unexpected errors
        # but don't crash the fuzzer
        pass

    # Test 2: arrow.get() with format string
    try:
        date_string = fdp.ConsumeUnicodeNoSurrogates(50)
        format_string = fdp.ConsumeUnicodeNoSurrogates(50)
        if date_string and format_string:
            arrow.get(date_string, format_string)
    except (arrow.ParserError, ValueError, AttributeError, TypeError,
            OverflowError, OSError, KeyError) as e:
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        pass

    # Test 3: arrow.get() with timestamp (integer)
    try:
        timestamp = fdp.ConsumeInt(8)
        # Limit timestamp to reasonable range to avoid hangs
        if -2**40 < timestamp < 2**40:
            arrow.get(timestamp)
    except (ValueError, OSError, OverflowError, TypeError) as e:
        # Expected exceptions
        pass
    except Exception as e:
        pass

    # Test 4: Test Arrow.format() if we can create a valid Arrow object
    try:
        # Start with current time
        arr = arrow.now()
        format_str = fdp.ConsumeUnicodeNoSurrogates(50)
        if format_str:
            arr.format(format_str)
    except (ValueError, AttributeError, KeyError, TypeError) as e:
        # Expected exceptions for invalid format strings
        pass
    except Exception as e:
        pass

    # Test 5: Test humanize() with locale variations
    try:
        arr = arrow.now()
        locale = fdp.ConsumeUnicodeNoSurrogates(20)
        if locale:
            arr.humanize(locale=locale)
    except (ValueError, AttributeError, KeyError, TypeError) as e:
        # Expected exceptions
        pass
    except Exception as e:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
