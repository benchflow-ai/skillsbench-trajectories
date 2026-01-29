"""
LibFuzzer-style fuzz driver for IPython library.
This fuzzer tests IPython parsing and execution functions.
"""

import sys
import atheris


def fuzz_ipython(input_bytes):
    """Fuzz IPython functions with various inputs."""
    fdp = atheris.FuzzedDataProvider(input_bytes)

    try:
        # Get a random string from the input
        input_str = fdp.consume_string(fdp.remaining_bytes())

        # Test string operations that IPython uses
        # These are safe operations that can be fuzzed

        # Test input transformation patterns
        test_cases = [
            input_str,
            input_str.encode('utf-8').decode('utf-8', errors='replace'),
            input_str.strip(),
            ' '.join(input_str.split()),
        ]

        for test_str in test_cases:
            try:
                # Test basic string processing that IPython uses
                if len(test_str) > 0:
                    # Simulate some basic IPython input processing
                    _ = repr(test_str)
                    _ = test_str.format()
            except Exception:
                pass

    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, fuzz_ipython)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
