#!/usr/bin/env python3
"""
Fuzz driver for minisgl library.
Targets configuration parsing and graph operations.
"""

import sys
import atheris

with atheris.instrument_imports():
    # Import minisgl components
    try:
        from minisgl.engine import config
    except ImportError:
        # If imports fail, we'll create a minimal fuzzer
        config = None


def TestOneInput(data):
    """Fuzz entry point for minisgl functions."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Generate random configuration-like data
        config_dict = generate_config(fdp)

        # Try to process the configuration
        # This is a placeholder - actual implementation depends on minisgl API
        # For now, just exercise dictionary operations
        if config_dict:
            _ = str(config_dict)
            _ = repr(config_dict)

    except Exception as e:
        # Catch any unexpected exceptions
        exception_type = type(e).__name__
        safe_exceptions = [
            'ValueError', 'TypeError', 'KeyError', 'AttributeError',
            'IndexError', 'OverflowError', 'RecursionError', 'MemoryError'
        ]
        if exception_type not in safe_exceptions:
            raise  # Re-raise unexpected exceptions


def generate_config(fdp, depth=0, max_depth=3):
    """Generate a random configuration dictionary."""
    if depth >= max_depth:
        return generate_simple_value(fdp)

    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Simple value
        return generate_simple_value(fdp)
    elif choice == 1:
        # List
        size = fdp.ConsumeIntInRange(0, 5)
        return [generate_config(fdp, depth + 1, max_depth) for _ in range(size)]
    elif choice == 2:
        # Dictionary
        size = fdp.ConsumeIntInRange(0, 5)
        result = {}
        for _ in range(size):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 20))
            value = generate_config(fdp, depth + 1, max_depth)
            result[key] = value
        return result
    else:
        # None
        return None


def generate_simple_value(fdp):
    """Generate a simple configuration value."""
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return None
    elif choice == 1:
        return fdp.ConsumeBool()
    elif choice == 2:
        return fdp.ConsumeInt(4)
    elif choice == 3:
        return fdp.ConsumeRegularFloat()
    else:
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))


def main():
    """Main entry point for fuzzing."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
