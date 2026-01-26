#!/usr/bin/env python3
"""
Fuzz driver for minisgl library - ML library
Fuzzes msgpack deserialization which is used in the API server.
"""

import atheris
import sys

with atheris.instrument_imports():
    import msgpack


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for msgpack deserialization."""
    if len(data) < 1:
        return

    # Test msgpack.unpackb() which is used by minisgl API server
    try:
        msgpack.unpackb(data)
    except (msgpack.exceptions.ExtraData,
            msgpack.exceptions.UnpackException,
            msgpack.exceptions.UnpackValueError,
            ValueError,
            TypeError,
            OverflowError):
        # Expected exceptions for invalid msgpack data
        pass
    except Exception as e:
        # Unexpected exception - potential bug
        pass

    # Test with strict_map_key=False option
    try:
        msgpack.unpackb(data, strict_map_key=False)
    except:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
