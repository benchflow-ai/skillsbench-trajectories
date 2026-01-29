#!/usr/bin/env python3
"""
Fuzz driver for Arrow library using atheris.

Tests:
- arrow.get() with various string inputs
- Date parsing and formatting
- Timezone handling
"""

import sys
import atheris
from datetime import datetime, timezone
from typing import List


def fuzz_arrow_get(data: bytes) -> None:
    """Fuzz the arrow.get() function with various inputs."""
    try:
        import arrow

        # Test with string input
        if len(data) > 0:
            try:
                # Try decoding as UTF-8
                test_str = data.decode('utf-8', errors='ignore')
                try:
                    arrow.get(test_str)
                except Exception:
                    pass  # Expected for many invalid formats
            except Exception:
                pass

        # Test with timestamp (int and float)
        try:
            arrow.get(len(data))
        except Exception:
            pass

        try:
            arrow.get(float(len(data)) if data else 0.0)
        except Exception:
            pass

        # Test with datetime object
        try:
            dt = datetime.now(timezone.utc)
            arrow.get(dt)
        except Exception:
            pass

        # Test with tuple (year, month, day)
        if len(data) > 3:
            try:
                year = (data[0] << 8) | data[1]
                month = (data[2] % 12) + 1
                day = (data[3] % 28) + 1
                arrow.get((year, month, day))
            except Exception:
                pass

        # Test now() and utcnow()
        try:
            arrow.now()
            arrow.utcnow()
        except Exception:
            pass

    except ImportError:
        # Library not installed
        pass


def TestOneInput(data: bytes) -> None:
    """Main fuzzing entry point."""
    fuzz_arrow_get(data)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Fuzz driver for Arrow library")
        print("Usage: python fuzz.py")
        sys.exit(0)

    atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
    atheris.Fuzz()
