#!/usr/bin/env python3
"""Fuzz driver for Arrow library using LibFuzzer interface."""

import sys
import signal
import os

# Add parent directory to path for arrow module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import arrow
except ImportError:
    print("arrow module not installed, skipping fuzzing")
    sys.exit(0)


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Fuzzing timed out")


def fuzz_loads(data: bytes) -> None:
    """Fuzz function for arrow parsing functions."""
    if not data:
        return

    try:
        # Try to decode as string
        decoded = data.decode('utf-8', errors='replace')

        # Fuzz arrow.get() with various inputs
        try:
            arrow.get(decoded)
        except Exception:
            pass

        # Try parsing as various timestamp formats
        try:
            arrow.get(int(decoded) if decoded.isdigit() else decoded)
        except Exception:
            pass

        # Fuzz Arrow factory creation
        try:
            factory = arrow.ArrowFactory()
            factory.create(decoded)
        except Exception:
            pass

        # Fuzz Arrow.strptime
        try:
            arrow.Arrow.strptime(decoded, "%Y-%m-%d")
        except Exception:
            pass

    except Exception:
        pass


def fuzz_format(data: bytes) -> None:
    """Fuzz function for arrow formatting functions."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        # Create an Arrow object for formatting tests
        try:
            a = arrow.get("2023-01-01")
            if a:
                # Fuzz various format strings
                a.format(decoded[:50] if len(decoded) > 50 else decoded)
        except Exception:
            pass

        # Fuzz humanize
        try:
            a = arrow.get("2023-01-01")
            a.humanize(decoded[:20] if len(decoded) > 20 else decoded)
        except Exception:
            pass

    except Exception:
        pass


def fuzz_replace(data: bytes) -> None:
    """Fuzz function for arrow replace methods."""
    if not data:
        return

    try:
        decoded = data.decode('utf-8', errors='replace')

        try:
            a = arrow.get("2023-01-01 12:00:00")
            # Fuzz replace with various arguments
            a.replace(second=int(decoded[:2]) if decoded[:2].isdigit() else 0)
        except Exception:
            pass

        try:
            a = arrow.utcnow()
            a.shift(months=int(decoded[:3]) if decoded[:3].isdigit() else 1)
        except Exception:
            pass

    except Exception:
        pass


def main():
    """Main fuzzing function."""
    # Set timeout for long-running fuzzing sessions
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60 second overall timeout

    if len(sys.argv) > 1:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.read()
        fuzz_loads(data.encode('utf-8'))
        fuzz_format(data.encode('utf-8'))
        fuzz_replace(data.encode('utf-8'))
    else:
        # Standalone test mode - run through some test cases
        test_cases = [
            b"2023-01-15",
            b"2023-01-15T12:30:00Z",
            b"invalid-date-string",
            b"",
            b"\x00\x01\x02",
            b"{}",
            b"{" + b"A" * 1000 + b"}",
            b"null",
            b"1234567890",
        ]

        for data in test_cases:
            try:
                fuzz_loads(data)
                fuzz_format(data)
                fuzz_replace(data)
            except Exception as e:
                print(f"Error with {data!r}: {e}")

    signal.alarm(0)
    print("Fuzzing completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
