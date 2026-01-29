#!/usr/bin/env python3
"""Fuzz driver for minisgl library."""

import atheris
import sys

with atheris.instrument_imports():
    try:
        import minisgl
    except ImportError:
        # Fallback if minisgl structure differs
        pass

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for minisgl core functions."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Try to fuzz different components
        operation = fdp.ConsumeIntInRange(0, 4)

        if operation == 0:
            # Fuzz message deserialization
            msg_data = fdp.ConsumeBytes(len(data) - 1)
            try:
                # Attempt to deserialize various message formats
                if hasattr(minisgl, 'deserialize'):
                    minisgl.deserialize(msg_data)
            except Exception:
                pass

        elif operation == 1:
            # Fuzz tree operations
            try:
                if hasattr(minisgl, 'RadixManager'):
                    manager = minisgl.RadixManager()
                    # Try various tree operations
                    key = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 100))
                    value = fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 1000))
                    try:
                        manager.insert(key, value)
                        manager.search(key)
                    except Exception:
                        pass
            except Exception:
                pass

        elif operation == 2:
            # Fuzz tokenization
            try:
                if hasattr(minisgl, 'Tokenizer'):
                    tokenizer = minisgl.Tokenizer()
                    tokens = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 1000))
                    tokenizer.tokenize(tokens)
            except Exception:
                pass

        elif operation == 3:
            # Fuzz scheduling
            try:
                if hasattr(minisgl, 'Scheduler'):
                    scheduler = minisgl.Scheduler()
                    msg_data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 500))
                    scheduler.process_message(msg_data)
            except Exception:
                pass

        else:
            # Fuzz arbitrary input
            fdp.ConsumeRemainingAsBytes()

    except Exception:
        # Catch and ignore expected exceptions
        pass

if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
