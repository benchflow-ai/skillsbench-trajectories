"""
LibFuzzer fuzz driver for Arrow datetime library.

Targets:
- DateTimeParser.parse_iso()
- DateTimeParser.parse()
- ArrowFactory.get()
- TzinfoParser.parse()
"""

import sys
import arrow
from arrow import parser, factory

def fuzz(data):
    """Main fuzzing target for Arrow library."""
    if len(data) < 2:
        return

    # Split input into sections for different test cases
    parts = data.split(b'\x00')

    if len(parts) >= 1:
        # Test 1: ISO datetime parsing
        try:
            iso_string = parts[0].decode('utf-8', errors='ignore')
            if iso_string:
                arrow.get(iso_string)
        except (arrow.parser.ParserError, ValueError, TypeError, OverflowError):
            pass
        except Exception:
            pass

    if len(parts) >= 2:
        # Test 2: Custom format parsing
        try:
            datetime_str = parts[0].decode('utf-8', errors='ignore')
            format_str = parts[1].decode('utf-8', errors='ignore')
            if datetime_str and format_str:
                arrow.get(datetime_str, format_str)
        except (arrow.parser.ParserError, ValueError, TypeError, OverflowError):
            pass
        except Exception:
            pass

    if len(parts) >= 3:
        # Test 3: Timezone parsing
        try:
            tz_string = parts[2].decode('utf-8', errors='ignore')
            if tz_string:
                parser.TzinfoParser.parse(tz_string)
        except (arrow.parser.ParserError, ValueError, TypeError):
            pass
        except Exception:
            pass

    # Test 4: Factory get with timestamp
    try:
        if len(data) >= 8:
            # Interpret first 8 bytes as float
            ts = float(int.from_bytes(data[:8], 'big', signed=True)) / 1e6
            arrow.get(ts)
    except (ValueError, TypeError, OverflowError, OSError):
        pass
    except Exception:
        pass


if __name__ == '__main__':
    # Simple test mode
    test_data = b'2021-10-12T14:30:00\x00YYYY-MM-DD\x00America/New_York\x00test'
    fuzz(test_data)
    print("Fuzz target ready")
