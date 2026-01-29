#!/usr/bin/env python3
"""Fuzz driver for Arrow - Python datetime library."""

import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Arrow datetime parsing and creation."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test arrow.get() - Main factory entry point
    try:
        mode = fdp.ConsumeIntInRange(0, 8)

        if mode == 0:
            # No arguments (now/utcnow)
            arrow.get()

        elif mode == 1:
            # Single timestamp
            timestamp = fdp.ConsumeFloat()
            arrow.get(timestamp)

        elif mode == 2:
            # ISO string
            iso_str = fdp.ConsumeUnicode(len(data))
            arrow.get(iso_str)

        elif mode == 3:
            # String with format
            date_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
            fmt = fdp.PickValueInList(['YYYY-MM-DD', 'DD/MM/YYYY', 'MM-DD-YYYY HH:mm:ss'])
            arrow.get(date_str, fmt)

        elif mode == 4:
            # String with format list (fallback)
            date_str = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
            formats = ['YYYY-MM-DD', 'DD/MM/YYYY', 'YYYY-MM-DD HH:mm:ss']
            arrow.get(date_str, formats)

        elif mode == 5:
            # Timestamp with timezone
            timestamp = fdp.ConsumeFloat()
            tz = fdp.PickValueInList(['UTC', 'US/Eastern', 'Europe/London', 'local'])
            arrow.get(timestamp, tz)

        elif mode == 6:
            # ISO week tuple (year, week, day)
            year = fdp.ConsumeIntInRange(1, 9999)
            week = fdp.ConsumeIntInRange(1, 53)
            day = fdp.ConsumeIntInRange(1, 7)
            try:
                arrow.get((year, week, day))
            except (ValueError, AttributeError):
                pass

        else:
            # String input
            date_str = fdp.ConsumeUnicode(len(data))
            arrow.get(date_str)

    except (ValueError, TypeError, arrow.parser.ParserError):
        # Expected exceptions
        pass
    except Exception:
        pass

    # Test DateTimeParser.parse_iso() - ISO 8601 parsing
    try:
        fdp = atheris.FuzzedDataProvider(data)
        iso_string = fdp.ConsumeUnicode(len(data))
        normalize = fdp.ConsumeBool()
        parser = DateTimeParser()
        parser.parse_iso(iso_string, normalize_whitespace=normalize)
    except (ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test DateTimeParser.parse() - Custom format parsing
    try:
        fdp = atheris.FuzzedDataProvider(data)
        date_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
        fmt = fdp.PickValueInList([
            'YYYY-MM-DD',
            'DD/MM/YYYY',
            'YYYY-MM-DD HH:mm:ss',
            'HH:mm:ss',
            'MMMM D, YYYY',
            'dddd, MMMM D, YYYY',
        ])
        parser = DateTimeParser()
        parser.parse(date_string, fmt)
    except (ValueError, AttributeError):
        pass
    except Exception:
        pass

    # Test TzinfoParser.parse() - Timezone parsing
    try:
        fdp = atheris.FuzzedDataProvider(data)
        tz_string = fdp.ConsumeUnicode(len(data))
        TzinfoParser.parse(tz_string)
    except Exception:
        pass

    # Test timezone edge cases
    try:
        fdp = atheris.FuzzedDataProvider(data)
        offset_sign = fdp.PickValueInList(['+', '-'])
        hours = fdp.ConsumeIntInRange(0, 14)
        minutes = fdp.ConsumeIntInRange(0, 59)
        tz_string = f"{offset_sign}{hours:02d}:{minutes:02d}"
        TzinfoParser.parse(tz_string)
    except Exception:
        pass

    # Test arrow object manipulation
    try:
        fdp = atheris.FuzzedDataProvider(data)
        # Create a base arrow object
        arr = arrow.now()

        # Test shift operations
        years = fdp.ConsumeIntInRange(-10, 10)
        months = fdp.ConsumeIntInRange(-12, 12)
        days = fdp.ConsumeIntInRange(-365, 365)
        arr.shift(years=years, months=months, days=days)

        # Test replace operations
        year = fdp.ConsumeIntInRange(1, 9999)
        month = fdp.ConsumeIntInRange(1, 12)
        day = fdp.ConsumeIntInRange(1, 28)
        try:
            arr.replace(year=year, month=month, day=day)
        except Exception:
            pass

    except Exception:
        pass

    # Test timestamp boundary values
    try:
        fdp = atheris.FuzzedDataProvider(data)
        timestamp = fdp.ConsumeIntInRange(-62135596800, 253402300799)  # Year 1-9999
        arrow.get(timestamp)
    except (ValueError, OverflowError):
        pass
    except Exception:
        pass

if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
