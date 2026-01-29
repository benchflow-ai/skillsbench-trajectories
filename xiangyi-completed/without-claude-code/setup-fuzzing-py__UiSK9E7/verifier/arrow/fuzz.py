#!/usr/bin/env python3
"""
Coverage-guided fuzzing driver for the Arrow library.
Uses atheris for LibFuzzer-style fuzzing.
"""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Arrow library."""
    # Import inside function to avoid issues during atheris setup
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser

    # Convert bytes to string for testing
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not text or len(text) > 10000:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: arrow.get() with string input
    try:
        arrow.get(text)
    except (ValueError, TypeError, arrow.parser.ParserError):
        pass
    except Exception:
        pass

    # Test 2: DateTimeParser.parse_iso()
    try:
        parser = DateTimeParser()
        parser.parse_iso(text)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 3: DateTimeParser.parse_iso() with normalize_whitespace
    try:
        parser = DateTimeParser()
        parser.parse_iso(text, normalize_whitespace=True)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 4: TzinfoParser.parse()
    try:
        tz_parser = TzinfoParser()
        tz_parser.parse(text)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 5: arrow.get() with format string
    # Generate a simple format string from fuzzed data
    if len(data) > 10:
        format_part = fdp.ConsumeUnicodeNoSurrogates(20)
        date_part = fdp.ConsumeUnicodeNoSurrogates(50)
        try:
            arrow.get(date_part, format_part)
        except (ValueError, TypeError, arrow.parser.ParserError):
            pass
        except Exception:
            pass

    # Test 6: arrow.get() with timestamp (float/int)
    try:
        if len(data) >= 8:
            # Try to parse as a timestamp
            import struct
            timestamp = struct.unpack("d", data[:8])[0]
            if -1e15 < timestamp < 1e15:  # Reasonable timestamp range
                arrow.get(timestamp)
    except (ValueError, TypeError, struct.error, OverflowError, OSError):
        pass
    except Exception:
        pass

    # Test 7: DateTimeParser.parse() with various format tokens
    format_tokens = [
        "YYYY-MM-DD",
        "YYYY/MM/DD",
        "YYYY.MM.DD",
        "YY-MM-DD",
        "MMMM D, YYYY",
        "MMM D, YYYY",
        "DD-MM-YYYY HH:mm:ss",
        "YYYY-MM-DDTHH:mm:ssZZ",
        "X",  # Unix timestamp
        "x",  # Unix timestamp in milliseconds
    ]

    if len(data) > 1:
        idx = data[0] % len(format_tokens)
        try:
            parser = DateTimeParser()
            parser.parse(text, format_tokens[idx])
        except (ValueError, TypeError):
            pass
        except Exception:
            pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
