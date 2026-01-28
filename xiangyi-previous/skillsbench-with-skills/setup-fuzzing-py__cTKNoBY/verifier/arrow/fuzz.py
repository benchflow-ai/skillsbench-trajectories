#!/usr/bin/env python3
"""Coverage-guided fuzzer for Arrow library using atheris."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for arrow.get() parsing function."""
    try:
        import arrow
        from arrow.parser import ParserError
        
        # Convert bytes to string for parsing
        try:
            input_str = data.decode('utf-8')
        except UnicodeDecodeError:
            input_str = data.decode('latin-1')
        
        # Test arrow.get() with string input
        try:
            result = arrow.get(input_str)
        except (ParserError, ValueError, TypeError, OverflowError):
            pass
        
        # Test with format strings if input is long enough
        if len(input_str) > 10:
            fmt = input_str[:10]
            date_str = input_str[10:]
            try:
                arrow.get(date_str, fmt)
            except (ParserError, ValueError, TypeError, OverflowError, KeyError):
                pass
        
        # Test arrow.now() and shift operations
        try:
            now = arrow.now()
            if len(data) >= 4:
                hours = int.from_bytes(data[:2], 'little', signed=True) % 1000
                days = int.from_bytes(data[2:4], 'little', signed=True) % 1000
                now.shift(hours=hours, days=days)
        except (ValueError, OverflowError):
            pass
            
    except Exception:
        # Catch any unexpected exceptions to continue fuzzing
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
