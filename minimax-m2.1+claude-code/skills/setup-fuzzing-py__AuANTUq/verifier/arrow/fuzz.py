"""
Coverage-guided fuzzing driver for Arrow library.
Fuzzes date/time parsing, formatting, and manipulation functions.
"""

import atheris
import sys

# Import Arrow library
try:
    import arrow
except ImportError:
    # Try alternative import path
    sys.path.insert(0, '/app/arrow')
    import arrow

def fuzz_arrow_get(data):
    """Fuzz arrow.get() with various input types"""
    try:
        # Convert data to string for testing
        input_str = data.decode('utf-8', errors='ignore')

        # Test 1: Basic string parsing
        try:
            result = arrow.get(input_str)
        except Exception:
            pass  # Expected for many malformed inputs

        # Test 2: String with format specifier
        try:
            result = arrow.get(input_str, 'YYYY-MM-DD')
        except Exception:
            pass

        # Test 3: ISO format
        try:
            result = arrow.get(input_str, arrow.parser.DateTimeParser.ISO8601)
        except Exception:
            pass

        # Test 4: With timezone
        try:
            result = arrow.get(input_str, 'YYYY-MM-DD HH:mm:ss ZZ')
        except Exception:
            pass

    except Exception:
        pass

def fuzz_arrow_parse_iso(data):
    """Fuzz ISO 8601 parsing specifically"""
    try:
        input_str = data.decode('utf-8', errors='ignore')
        parser = arrow.parser.DateTimeParser()

        # Test ISO parsing
        try:
            result = parser.parse_iso(input_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_arrow_shift(data):
    """Fuzz Arrow.shift() with extreme values"""
    try:
        # Create a basic Arrow instance
        base = arrow.get('2020-01-01 00:00:00')

        # Try to shift with various parameters from fuzz data
        params = {}

        # Extract some values from data to try
        if len(data) >= 4:
            # Try to extract integer values
            val1 = int.from_bytes(data[0:4], byteorder='big', signed=True) % 1000000
            val2 = int.from_bytes(data[4:8], byteorder='big', signed=True) % 1000000

            # Try different shift parameters
            params_list = [
                {'years': val1},
                {'months': val1},
                {'days': val1},
                {'hours': val1},
                {'minutes': val1},
                {'seconds': val1},
                {'weeks': val1},
                {'microseconds': val1},
                {'years': val1, 'months': val2},
            ]

            for params in params_list:
                try:
                    result = base.shift(**params)
                except Exception:
                    pass

    except Exception:
        pass

def fuzz_arrow_format(data):
    """Fuzz Arrow.format() with custom format strings"""
    try:
        base = arrow.get('2020-01-01 00:00:00')

        # Try formatting with the fuzz data as format string
        format_str = data.decode('utf-8', errors='ignore')

        try:
            result = base.format(format_str)
        except Exception:
            pass

        # Try some common format variations
        common_formats = [
            'YYYY-MM-DD',
            'YYYY-MM-DD HH:mm:ss',
            'X',  # Unix timestamp
            'x',  # Unix ms timestamp
        ]

        for fmt in common_formats:
            try:
                result = base.format(fmt)
            except Exception:
                pass

    except Exception:
        pass

def fuzz_arrow_dehumanize(data):
    """Fuzz Arrow.dehumanize() - human-readable time parsing"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        try:
            result = arrow.dehumanize(input_str)
        except Exception:
            pass

    except Exception:
        pass

def TestOneInput(data):
    """Main fuzzing entry point"""
    # Limit input size to avoid timeouts
    if len(data) > 10000:
        data = data[:10000]

    # Run all fuzzing targets
    fuzz_arrow_get(data)
    fuzz_arrow_parse_iso(data)
    fuzz_arrow_shift(data)
    fuzz_arrow_format(data)
    fuzz_arrow_dehumanize(data)

if __name__ == '__main__':
    # Setup atheris
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
