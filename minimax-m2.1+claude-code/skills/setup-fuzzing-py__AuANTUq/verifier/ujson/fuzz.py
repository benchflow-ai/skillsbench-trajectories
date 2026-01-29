"""
Coverage-guided fuzzing driver for ujson library.
Fuzzes JSON encoding/decoding with focus on string parsing and memory safety.
"""

import atheris
import sys

# Import ujson library
try:
    import ujson
except ImportError:
    sys.path.insert(0, '/app/ujson')
    import ujson

def fuzz_loads(data):
    """Fuzz JSON decoding with ujson.loads()"""
    try:
        # Convert data to string
        input_str = data.decode('utf-8', errors='ignore')

        # Test basic loads
        try:
            result = ujson.loads(input_str)
        except Exception:
            pass

        # Test with different decode functions
        try:
            result = ujson.decode(input_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_loads_invalid_utf8(data):
    """Fuzz JSON decoding with invalid UTF-8 sequences"""
    try:
        # Test with raw bytes containing invalid UTF-8
        try:
            result = ujson.loads(data)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_dumps(data):
    """Fuzz JSON encoding with ujson.dumps()"""
    try:
        # Try to encode the fuzz data directly as a string
        input_str = data.decode('utf-8', errors='ignore')

        try:
            result = ujson.dumps(input_str)
        except Exception:
            pass

        # Try encoding as dict
        try:
            test_dict = {
                "key": input_str[:100],  # Limit length
                "number": 42,
                "nested": {"inner": "value"}
            }
            result = ujson.dumps(test_dict)
        except Exception:
            pass

        # Try encoding as list
        try:
            test_list = [input_str[:100] for _ in range(5)]
            result = ujson.dumps(test_list)
        except Exception:
            pass

        # Test with custom parameters
        try:
            result = ujson.dumps(input_str, ensure_ascii=False)
        except Exception:
            pass

        try:
            result = ujson.dumps(input_str, encode_html_chars=True)
        except Exception:
            pass

        try:
            result = ujson.dumps(input_str, escape_forward_slashes=True)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_dumps_with_separators(data):
    """Fuzz dumps() with custom separators (common source of bugs)"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Extract potential separator strings from data
        if len(data) >= 2:
            sep1 = data[:len(data)//2]
            sep2 = data[len(data)//2:]

            # Try to convert to strings safely
            try:
                sep1_str = sep1.decode('utf-8', errors='ignore')
                sep2_str = sep2.decode('utf-8', errors='ignore')

                # Test with custom separators
                test_dict = {"key": "value", "key2": "value2"}
                result = ujson.dumps(test_dict, separators=(sep1_str[:10], sep2_str[:10]))
            except Exception:
                pass

    except Exception:
        pass

def fuzz_dumps_number_edge_cases(data):
    """Fuzz dumps() with number edge cases"""
    try:
        # Extract numbers from fuzz data
        if len(data) >= 4:
            # Try different integer interpretations
            for i in range(min(10, len(data) - 4)):
                try:
                    num = int.from_bytes(data[i:i+4], byteorder='big', signed=True)
                    result = ujson.dumps(num)
                except Exception:
                    pass

            # Try floating point
            if len(data) >= 8:
                try:
                    import struct
                    float_val = struct.unpack('d', data[:8])[0]
                    result = ujson.dumps(float_val)
                except Exception:
                    pass

        # Test special float values
        special_floats = [float('inf'), float('-inf'), float('nan')]
        for val in special_floats:
            try:
                result = ujson.dumps(val)
            except Exception:
                pass

    except Exception:
        pass

def fuzz_loads_malformed_strings(data):
    """Fuzz loads() with malformed escape sequences"""
    try:
        # These are common sources of bugs in JSON parsers
        malformed_strings = [
            b'{"key": "value\\"}',  # Unterminated escape
            b'{"key": "value\\x"}',  # Incomplete hex escape
            b'{"key": "value\\u"}',  # Incomplete unicode escape
            b'{"key": "value\\u123"}',  # Incomplete unicode escape (3 digits)
            b'{"key": "value\\u12"}',  # Incomplete unicode escape (2 digits)
            b'{"key": "value\\u1"}',   # Incomplete unicode escape (1 digit)
            b'{"key": "\\"}',           # Just a backslash
            b'{"key": "\\x"}',          # Just \x
            b'{"key": "\\u"}',          # Just \u
            b'{"key": "\\u12"}',        # \u with only 2 digits
        ]

        for malformed in malformed_strings:
            try:
                result = ujson.loads(malformed)
            except Exception:
                pass

    except Exception:
        pass

def fuzz_loads_unicode_edge_cases(data):
    """Fuzz loads() with Unicode edge cases"""
    try:
        # Test with overlong UTF-8 sequences (security issue)
        # 2-byte encoding of ASCII character
        overlong_ascii = b'"\xc0\x80"'  # Overlong encoding of NUL
        try:
            result = ujson.loads(overlong_ascii)
        except Exception:
            pass

        # Test with invalid UTF-16 surrogates
        invalid_surrogates = [
            b'{"key": "\\ud800"}',      # High surrogate without low
            b'{"key": "\\udc00"}',      # Low surrogate without high
            b'{"key": "\\ud800\\ud800"}',  # Two high surrogates
        ]

        for test_case in invalid_surrogates:
            try:
                result = ujson.loads(test_case)
            except Exception:
                pass

    except Exception:
        pass

def TestOneInput(data):
    """Main fuzzing entry point"""
    # Limit input size to avoid timeouts
    if len(data) > 100000:
        data = data[:100000]

    # Run all fuzzing targets
    fuzz_loads(data)
    fuzz_loads_invalid_utf8(data)
    fuzz_dumps(data)
    fuzz_dumps_with_separators(data)
    fuzz_dumps_number_edge_cases(data)
    fuzz_loads_malformed_strings(data)
    fuzz_loads_unicode_edge_cases(data)

if __name__ == '__main__':
    # Setup atheris
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
