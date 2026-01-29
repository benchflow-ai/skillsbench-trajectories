#!/usr/bin/env python3
"""LibFuzzer harness for Arrow date/time library."""

import sys
import atheris

try:
    import arrow
    from arrow import parser
except ImportError as e:
    print(f"Failed to import arrow: {e}", file=sys.stderr)
    sys.exit(1)


def fuzz_arrow_parse(data: bytes) -> None:
    """Fuzz arrow.parser.DateTimeParser.parse()"""
    try:
        # Convert bytes to string
        input_str = data.decode('utf-8', errors='ignore')

        # Try to parse with arrow
        parser_obj = parser.DateTimeParser()

        # Test various parsing scenarios
        try:
            parser_obj.parse(input_str)
        except (parser.ParserError, ValueError, TypeError):
            pass

        try:
            parser_obj.parse(input_str, 'YYYY-MM-DD')
        except (parser.ParserError, ValueError, TypeError):
            pass

        try:
            arrow.get(input_str)
        except Exception:
            pass

    except (UnicodeDecodeError, MemoryError, RuntimeError):
        pass


def fuzz_arrow_factory(data: bytes) -> None:
    """Fuzz arrow.factory.ArrowFactory.get()"""
    try:
        # Use data as input for factory
        input_str = data.decode('utf-8', errors='ignore')

        try:
            arrow.get(input_str)
        except Exception:
            pass

        # Try with partial data as timestamp
        try:
            if len(data) >= 4:
                timestamp = int.from_bytes(data[:4], 'big', signed=False) / 1000.0
                arrow.get(timestamp)
        except Exception:
            pass

    except Exception:
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing function."""
    fuzz_arrow_parse(data)
    fuzz_arrow_factory(data)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
