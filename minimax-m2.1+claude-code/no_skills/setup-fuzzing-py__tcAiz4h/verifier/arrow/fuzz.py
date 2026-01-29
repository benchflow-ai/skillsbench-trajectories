"""
LibFuzzer-style fuzz driver for Arrow library.
This fuzzer tests arrow.get() with various datetime string inputs.
"""

import sys
import atheris

import arrow


def fuzz_get(input_bytes):
    """Fuzz the arrow.get() function with various inputs."""
    fdp = atheris.FuzzedDataProvider(input_bytes)

    try:
        # Get a random string from the input
        input_str = fdp.consume_string(fdp.remaining_bytes())

        # Try different ways to call arrow.get()
        import random
        method = random.randint(0, 4)

        if method == 0:
            # Parse as string directly
            arrow.get(input_str)
        elif method == 1:
            # Parse with default format
            arrow.get(input_str, "YYYY-MM-DD")
        elif method == 2:
            # Parse with ISO format
            arrow.get(input_str, "YYYY-MM-DD HH:mm:ss")
        elif method == 3:
            # Try parsing as timestamp (if it looks numeric)
            if input_str.strip().isdigit():
                arrow.get(int(input_str.strip()))
            else:
                # Try float timestamp
                try:
                    arrow.get(float(input_str))
                except (ValueError, TypeError):
                    pass
        else:
            # Try with different locales
            locales = ["en-us", "fr", "de", "es", "pt"]
            locale = locales[random.randint(0, len(locales) - 1)]
            try:
                arrow.get(input_str, locale=locale)
            except Exception:
                pass
    except Exception:
        # Expected: various parsing errors are normal
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, fuzz_get)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
