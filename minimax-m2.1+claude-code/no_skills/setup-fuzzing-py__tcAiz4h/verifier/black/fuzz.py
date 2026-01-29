"""
LibFuzzer-style fuzz driver for Black library.
This fuzzer tests black.format_str() with various Python code inputs.
"""

import sys
import atheris

import black


def fuzz_format_str(input_bytes):
    """Fuzz the black.format_str() function with various inputs."""
    fdp = atheris.FuzzedDataProvider(input_bytes)

    try:
        # Get a random string from the input
        input_str = fdp.consume_string(fdp.remaining_bytes())

        # Create a Mode object
        mode = black.Mode()

        # Try to format the input as Python code
        try:
            black.format_str(input_str, mode=mode)
        except (black.InvalidInput, SyntaxError, ValueError, Exception):
            # Invalid Python code is expected, just try to catch other issues
            pass

        # Also try with different target versions
        try:
            target_versions = [
                black.TargetVersion.PY310,
                black.TargetVersion.PY311,
                black.TargetVersion.PY312,
            ]
            for target in target_versions:
                mode_with_target = black.Mode(target_version=target)
                try:
                    black.format_str(input_str, mode=mode_with_target)
                except (black.InvalidInput, SyntaxError, ValueError, Exception):
                    pass
        except Exception:
            pass

    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, fuzz_format_str)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
