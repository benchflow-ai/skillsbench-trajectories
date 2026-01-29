#!/usr/bin/env python3
"""Fuzz driver for Arrow - datetime/timezone library"""

import atheris
import sys
import struct

# Import arrow for fuzzing
import arrow


@atheris.instrument_func
def test_one(data):
    """Fuzz driver for arrow library"""
    if len(data) < 1:
        return

    # Test 1: ISO datetime parsing
    try:
        input_str = data.decode('utf-8', errors='ignore')
        if len(input_str) > 0 and len(input_str) < 1000:
            result = arrow.get(input_str)
    except (ValueError, TypeError, arrow.parser.ParserError):
        pass
    except Exception:
        raise

    # Test 2: Format string parsing
    try:
        if len(data) >= 4:
            parts = data.split(b'|', 1)
            if len(parts) == 2:
                datetime_str = parts[0].decode('utf-8', errors='ignore')
                fmt_str = parts[1].decode('utf-8', errors='ignore')

                if len(datetime_str) < 500 and len(fmt_str) < 100:
                    result = arrow.get(datetime_str, fmt_str)
    except (ValueError, TypeError, arrow.parser.ParserError):
        pass
    except Exception:
        raise

    # Test 3: Timezone parsing
    try:
        if len(data) > 0:
            tz_str = data[:min(len(data), 100)].decode('utf-8', errors='ignore')
            result = arrow.get('2023-01-01', tzinfo=tz_str)
    except (ValueError, TypeError, arrow.parser.ParserError):
        pass
    except Exception:
        raise

    # Test 4: Numeric timestamp parsing
    try:
        if len(data) >= 8:
            timestamp = struct.unpack('<d', data[:8])[0]
            if -1e10 < timestamp < 1e10:  # Reasonable timestamp range
                result = arrow.get(timestamp)
    except (ValueError, TypeError, OverflowError):
        pass
    except Exception:
        raise

    # Test 5: Format to string
    try:
        if len(data) > 0:
            fmt_str = data[:min(len(data), 100)].decode('utf-8', errors='ignore')
            result = arrow.now().format(fmt_str)
    except (ValueError, TypeError):
        pass
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
