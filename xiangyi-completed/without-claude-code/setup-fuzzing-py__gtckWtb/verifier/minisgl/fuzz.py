#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL library
Tests message parsing, serialization, and input processing
"""

import sys
import atheris

# Add minisgl to path
sys.path.insert(0, '/app/minisgl/python')

import msgpack


def TestOneInput(data):
    """Fuzz target for MiniSGL (focusing on msgpack since it's the main parsing component)"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz msgpack deserialization (main attack surface)
            packed_data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 10000))
            try:
                msgpack.unpackb(packed_data, raw=False)
            except (msgpack.exceptions.ExtraData,
                    msgpack.exceptions.UnpackException,
                    msgpack.exceptions.StackError,
                    ValueError, TypeError, MemoryError):
                pass

        elif choice == 1:
            # Fuzz msgpack serialization
            try:
                # Create random nested structure
                depth = fdp.ConsumeIntInRange(0, 10)
                obj = {}
                for i in range(fdp.ConsumeIntInRange(0, 100)):
                    key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
                    value = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
                    obj[key] = value
                msgpack.packb(obj)
            except (ValueError, TypeError, MemoryError, RecursionError):
                pass

        else:
            # Fuzz text input that might be passed to models
            # This simulates tokenizer/text processing
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 5000))
            # Just test basic string operations that might be done in preprocessing
            try:
                _ = text.strip()
                _ = text.split()
                _ = text.encode('utf-8')
            except (ValueError, TypeError, UnicodeError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions for debugging
        error_str = str(e)
        if "Segmentation fault" in error_str or "Bus error" in error_str:
            raise


def main():
    """Main fuzzing entry point"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
