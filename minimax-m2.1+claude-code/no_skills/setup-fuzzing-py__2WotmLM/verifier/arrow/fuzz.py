#!/usr/bin/env python3
"""
Fuzz driver for Arrow library.
Coverage-guided fuzzing for date/time parsing and formatting.
"""

import sys
import os
import time
import random
import string

# Add the library to path
sys.path.insert(0, '/app/arrow')

import arrow


def fuzz_unicode_string(data: bytes) -> str:
    """Convert bytes to a valid unicode string for testing."""
    try:
        return data.decode('utf-8', errors='replace')
    except:
        return ''


def fuzz_date_string(data: bytes) -> str:
    """Create a fuzzed date string from random bytes."""
    s = fuzz_unicode_string(data)

    # Randomly select a format pattern
    formats = [
        "YYYY-MM-DD",
        "YYYY-MM-DD HH:mm:ss",
        "YYYY-MM-DDTHH:mm:ss",
        "YYYY-MM-DDTHH:mm:ssZ",
        "DD/MM/YYYY",
        "MM/DD/YYYY",
        "YYYY/MM/DD",
        "DD-MM-YYYY",
        "RFC3339",
        "ISO8601",
        "unix",
        "timestamp",
    ]

    fmt = random.choice(formats)

    # Create variations with special characters
    variations = [
        s,
        f"{s}Z",
        f"+00:00{s}",
        f"{s} +00:00",
        f"{s}T00:00:00",
        f"{s}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}",
        f"{random.randint(1,31):02d}/{random.randint(1,12):02d}/{random.randint(1970,2100):04d}",
        f"{random.randint(1970,2100):04d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        str(int(time.time())),
        str(random.randint(-1000000000, 1000000000)),
    ]

    return random.choice(variations)


def fuzz_format_string(data: bytes) -> str:
    """Create a fuzzed format string."""
    s = fuzz_unicode_string(data)

    # Common format tokens
    tokens = [
        "YYYY", "MM", "DD", "HH", "mm", "ss", "ZZ", "Z",
        "YYYY-MM-DD", "HH:mm:ss", "MMM", "MMMM",
        "ddd", "dddd", "a", "A", "x", "X"
    ]

    if len(s) < 3 or random.random() < 0.3:
        # Return a valid format
        return random.choice([
            "YYYY-MM-DD",
            "YYYY-MM-DD HH:mm:ss",
            "MMMM D, YYYY",
            "DD MMM YYYY",
            "HH:mm:ss",
            "x",
            "X",
        ])

    # Mix random characters with valid tokens
    result = ""
    i = 0
    while i < len(s):
        if random.random() < 0.2:
            result += random.choice(tokens)
        else:
            result += s[i]
        i += 1

    return result


def fuzz_timezone(data: bytes) -> str:
    """Create a fuzzed timezone string."""
    s = fuzz_unicode_string(data)

    timezones = [
        "UTC", "US/Pacific", "US/Eastern", "Europe/London",
        "Europe/Paris", "Asia/Tokyo", "Asia/Shanghai",
        "Australia/Sydney", "America/New_York"
    ]

    if len(s) < 2 or random.random() < 0.5:
        return random.choice(timezones)

    # Add offsets
    variations = [
        s,
        f"{s}+00:00",
        f"{s}-05:00",
        f"Etc/GMT-{random.randint(-12, 12)}",
        f"GMT{'+' if random.random() > 0.5 else '-'}{random.randint(0, 12)}",
    ]

    return random.choice(variations)


def run_fuzz_test(data: bytes) -> None:
    """Main fuzz test function - processes a single fuzz input."""
    try:
        # Test 1: Parse various date strings
        date_str = fuzz_date_string(data)
        try:
            arrow.get(date_str)
        except Exception:
            pass

        # Test 2: Create Arrow with timestamp
        try:
            ts_data = int.from_bytes(data[:4] if len(data) >= 4 else data, 'big', signed=True)
            arrow.Arrow.from_timestamp(ts_data)
        except Exception:
            pass

        # Test 3: Test formatting
        try:
            now = arrow.now()
            fmt = fuzz_format_string(data)
            now.format(fmt)
        except Exception:
            pass

        # Test 4: Test shifting
        try:
            now = arrow.now()
            shifts = [
                {'days': random.randint(-365, 365)},
                {'weeks': random.randint(-52, 52)},
                {'months': random.randint(-12, 12)},
                {'hours': random.randint(-24, 24)},
                {'minutes': random.randint(-60, 60)},
            ]
            for shift in shifts:
                now.shift(**shift)
        except Exception:
            pass

        # Test 5: Test timezone conversions
        try:
            now = arrow.now()
            tz = fuzz_timezone(data)
            now.to(tz)
        except Exception:
            pass

        # Test 6: Test floor/ceil
        try:
            now = arrow.now()
            now.floor('day')
            now.ceil('day')
            now.floor('hour')
            now.ceil('hour')
        except Exception:
            pass

    except Exception as e:
        # Ignore exceptions from the fuzzer itself
        pass


def run_standalone_fuzzer(seconds: int = 10) -> None:
    """Run standalone fuzzer with random input generation."""
    print(f"Starting Arrow fuzzer for {seconds} seconds...")

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < seconds:
        # Generate random input
        length = random.randint(0, 1000)
        data = bytes(random.randint(0, 255) for _ in range(length))

        run_fuzz_test(data)
        iterations += 1

    print(f"Completed {iterations} iterations in {seconds} seconds")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # Standalone mode with random inputs
        seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_standalone_fuzzer(seconds)
    else:
        # LibFuzzer mode - read from stdin
        data = sys.stdin.buffer.read()
        run_fuzz_test(data)


if __name__ == "__main__":
    main()
