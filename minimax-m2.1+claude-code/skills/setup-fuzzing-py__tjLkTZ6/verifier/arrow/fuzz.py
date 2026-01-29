#!/usr/bin/env python3
"""
Fuzz driver for Arrow library
Fuzzes datetime parsing functions
"""
import sys
import random
import string
import arrow
from arrow.parser import DateTimeParser, ParserError


def fuzz_parse():
    """Fuzz the DateTimeParser.parse() function"""
    parser = DateTimeParser()

    # Generate random datetime strings
    test_cases = [
        # Random ISO-like formats
        f"{random.randint(1990, 2030)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        f"{random.randint(1990, 2030)}/{random.randint(1, 12)}/{random.randint(1, 28)}",
        f"{random.randint(1990, 2030)}.{random.randint(1, 12)}.{random.randint(1, 28)}",
        # Random strings
        ''.join(random.choices(string.ascii_letters + string.digits + ' -:/', k=random.randint(0, 100))),
        # Special characters and edge cases
        ' ' * random.randint(0, 20),
        '\x00' * random.randint(0, 10),
        '🎉' * random.randint(0, 10),
    ]

    for _ in range(100):
        test_input = random.choice(test_cases)
        fmt = random.choice([
            'YYYY-MM-DD',
            'YYYY/MM/DD',
            'YYYY.MM.DD',
            'YYYY-MM-DD HH:mm:ss',
            'YYYY-MM-DDTHH:mm:ss',
            [random.choice([
                'YYYY-MM-DD',
                'YYYY/MM/DD',
                'DD/MM/YYYY',
                'MM/DD/YYYY',
            ]) for _ in range(random.randint(1, 3))]
        ])

        try:
            result = parser.parse(test_input, fmt)
            # Use the result to prevent optimization
            assert result is not None
        except (ParserError, ValueError, TypeError) as e:
            # Expected for invalid input
            pass
        except Exception as e:
            # Unexpected exception
            print(f"Unexpected error in parse: {e}", file=sys.stderr)
            raise


def fuzz_parse_iso():
    """Fuzz the DateTimeParser.parse_iso() function"""
    parser = DateTimeParser()

    # Generate various ISO-like strings
    test_cases = [
        f"{random.randint(1990, 2030)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        f"{random.randint(1990, 2030)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
        f"{random.randint(1990, 2030)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}",
        f"{random.randint(1990, 2030)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}.{random.randint(0, 999999):06d}",
        # Edge cases
        ''.join(random.choices(string.printable, k=random.randint(0, 100))),
        'invalid-date-string',
        '2020-13-01',  # Invalid month
        '2020-01-32',  # Invalid day
        '25:00:00',  # Invalid hour
    ]

    for _ in range(100):
        test_input = random.choice(test_cases)
        normalize_ws = random.choice([True, False])

        try:
            result = parser.parse_iso(test_input, normalize_whitespace=normalize_ws)
            assert result is not None
        except (ParserError, ValueError) as e:
            # Expected for invalid input
            pass
        except Exception as e:
            print(f"Unexpected error in parse_iso: {e}", file=sys.stderr)
            raise


def fuzz_arrow_get():
    """Fuzz the Arrow.get() function"""
    # Test various input types
    test_inputs = [
        # Valid datetime strings
        f"{random.randint(1990, 2030)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        # Random strings
        ''.join(random.choices(string.ascii_letters + string.digits + ' -:/', k=random.randint(0, 100))),
        # Numbers (timestamps)
        random.randint(0, 2**31),
        # Tuples
        (random.randint(2020, 2023), random.randint(1, 12), random.randint(1, 28)),
        # Edge cases
        '',
        ' ' * 20,
        '\x00',
    ]

    for _ in range(100):
        test_input = random.choice(test_inputs)

        try:
            if isinstance(test_input, str):
                result = arrow.get(test_input, random.choice([
                    'YYYY-MM-DD',
                    'YYYY/MM/DD',
                    None
                ]))
            else:
                result = arrow.get(test_input)

            assert result is not None
        except (ParserError, ValueError, TypeError) as e:
            # Expected for invalid input
            pass
        except Exception as e:
            print(f"Unexpected error in get: {e}", file=sys.stderr)
            raise


if __name__ == '__main__':
    print("Starting Arrow fuzzing...")
    fuzz_parse()
    print("✓ parse() fuzzed successfully")
    fuzz_parse_iso()
    print("✓ parse_iso() fuzzed successfully")
    fuzz_arrow_get()
    print("✓ get() fuzzed successfully")
    print("Arrow fuzzing completed successfully!")
