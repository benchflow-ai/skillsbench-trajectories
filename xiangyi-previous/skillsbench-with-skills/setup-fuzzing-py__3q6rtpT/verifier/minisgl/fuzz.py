#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL library
Basic fuzzer - may need updates based on actual library structure
"""

import sys
import atheris

# Try to import minisgl components
try:
    with atheris.instrument_imports():
        # Import based on what we found in the directory
        import sys
        sys.path.insert(0, '/app/minisgl/python')
        # Basic fuzzer that can be extended once we know the API
except ImportError:
    pass

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for MiniSGL"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Basic fuzzing - extend based on actual library API
    try:
        # Placeholder - will be updated based on library structure
        text_input = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 200))
        # Add actual library calls here once we explore the API
    except Exception as e:
        # Catch all exceptions for now
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
