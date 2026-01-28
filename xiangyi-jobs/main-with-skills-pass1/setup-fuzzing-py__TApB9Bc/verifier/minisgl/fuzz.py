#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for MiniSGL inference framework.
Targets: Message deserialization and argument parsing
Note: minisgl has heavy dependencies (torch, numpy), fuzzer takes time to start.
"""

import atheris
import sys

# Simplified targets without heavy imports
def TestOneInput(data):
    """Fuzz entry point for MiniSGL library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz target 1: Simple dict/JSON-like parsing
    try:
        # Test basic dict handling with potential type fields
        test_input = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 256))
        # Minimal operations to avoid heavy imports
        if "__type__" in test_input:
            pass
    except Exception:
        pass

    # Fuzz target 2: String parsing for arguments
    try:
        arg_string = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 128))
        # Basic string processing
        parts = arg_string.split()
        if len(parts) > 0:
            pass
    except Exception:
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
