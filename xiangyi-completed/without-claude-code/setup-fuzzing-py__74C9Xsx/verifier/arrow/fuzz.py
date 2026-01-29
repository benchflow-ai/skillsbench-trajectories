"""
Fuzz driver for Arrow library.
Focus: DateTime parsing functionality
"""

import arrow
from arrow import parser
import time

def fuzz_arrow_get(data):
    """Fuzz arrow.get() with various string inputs"""
    try:
        arrow.get(data.decode('utf-8', errors='ignore'))
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_arrow_get: {type(e).__name__}")

def fuzz_arrow_parser(data):
    """Fuzz DateTimeParser.parse() with format strings"""
    try:
        if len(data) > 1:
            mid = len(data) // 2
            dt_str = data[:mid].decode('utf-8', errors='ignore')
            fmt_str = data[mid:].decode('utf-8', errors='ignore')

            p = parser.DateTimeParser()
            p.parse(dt_str, fmt_str)
    except (ValueError, TypeError, AttributeError, KeyError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_arrow_parser: {type(e).__name__}")

def fuzz_arrow_iso_parse(data):
    """Fuzz ISO 8601 parsing"""
    try:
        iso_str = data.decode('utf-8', errors='ignore')
        p = parser.DateTimeParser()
        p.parse_iso(iso_str)
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_arrow_iso_parse: {type(e).__name__}")

def main():
    """Main fuzzing function"""
    test_cases = [
        b"2023-01-01",
        b"2023-01-01T00:00:00",
        b"2023/01/01",
        b"01/01/2023",
        b"invalid date",
        b"" * 100,
        b"\x00" * 50,
        b"\xff" * 50,
        b"2025-12-31T23:59:59Z",
    ]

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < 10:
        for test_data in test_cases:
            choice = iterations % 3
            if choice == 0:
                fuzz_arrow_get(test_data)
            elif choice == 1:
                fuzz_arrow_parser(test_data)
            else:
                fuzz_arrow_iso_parse(test_data)
            iterations += 1

    print(f"Arrow fuzzer: Completed {iterations} iterations in 10 seconds")

if __name__ == "__main__":
    main()
