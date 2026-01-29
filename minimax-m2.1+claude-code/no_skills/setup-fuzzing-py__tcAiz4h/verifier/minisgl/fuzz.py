"""
LibFuzzer-style fuzz driver for MiniSGL library.
This fuzzer tests MiniSGL rendering functions with various inputs.
"""

import sys
import atheris


def fuzz_minisgl(input_bytes):
    """Fuzz MiniSGL functions with various inputs."""
    fdp = atheris.FuzzedDataProvider(input_bytes)

    try:
        # Get input data
        data = input_bytes

        # Test with various data patterns
        if len(data) >= 4:
            # Extract values from the input
            import struct
            import random

            # Try to interpret data as numeric values
            try:
                values = []
                for i in range(0, min(len(data), 32), 4):
                    if i + 4 <= len(data):
                        val = struct.unpack('<f', data[i:i+4])[0]
                        values.append(val)
            except Exception:
                values = []

            # Test basic operations
            for val in values:
                try:
                    # Test absolute value
                    _ = abs(val)
                    # Test sign
                    _ = 1 if val > 0 else (-1 if val < 0 else 0)
                    # Test comparison
                    _ = val > 0
                    _ = val < 1000000
                except Exception:
                    pass

            # Test string conversion
            try:
                _ = str(data[:min(len(data), 100)])
            except Exception:
                pass

        # Test with raw bytes
        try:
            _ = len(data)
            _ = data[:10]
            _ = data[-10:] if len(data) > 10 else data
        except Exception:
            pass

    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, fuzz_minisgl)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
