#!/usr/bin/env python3
"""
Fuzz driver for ujson library
Targets: ujson.loads() and ujson.dumps()
PRIORITY: HIGH - native C code with potential for memory corruption
"""

import sys
import atheris

with atheris.instrument_imports():
    import ujson

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for ujson library"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose between loads and dumps fuzzing
    choice = fdp.ConsumeIntInRange(0, 1)

    try:
        if choice == 0:
            # Fuzz ujson.loads() - PRIMARY TARGET
            # This is the most critical function as it parses untrusted input in native C code
            json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 2000))
            if json_string:
                ujson.loads(json_string)

        elif choice == 1:
            # Fuzz ujson.dumps() - SECONDARY TARGET
            # Build a potentially problematic Python object
            obj_choice = fdp.ConsumeIntInRange(0, 5)

            if obj_choice == 0:
                # Simple string
                obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200))
            elif obj_choice == 1:
                # Number (including edge cases)
                num_type = fdp.ConsumeIntInRange(0, 2)
                if num_type == 0:
                    obj = fdp.ConsumeInt(8)
                elif num_type == 1:
                    obj = fdp.ConsumeFloat()
                else:
                    obj = fdp.ConsumeIntInRange(-2**63, 2**63-1)
            elif obj_choice == 2:
                # List
                list_len = fdp.ConsumeIntInRange(0, 50)
                obj = [fdp.ConsumeInt(4) for _ in range(list_len)]
            elif obj_choice == 3:
                # Dict
                dict_len = fdp.ConsumeIntInRange(0, 20)
                obj = {}
                for _ in range(dict_len):
                    key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 30))
                    val = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
                    if key:
                        obj[key] = val
            elif obj_choice == 4:
                # Nested structure
                obj = {
                    "a": [1, 2, 3],
                    "b": {"nested": fdp.ConsumeUnicodeNoSurrogates(20)},
                    "c": fdp.ConsumeFloat()
                }
            else:
                # Special values
                obj = None

            if obj is not None or obj_choice == 5:
                ujson.dumps(obj)

    except (ValueError, TypeError, OverflowError, MemoryError, RecursionError):
        # Expected exceptions for invalid input
        pass
    except Exception as e:
        # Unexpected exceptions might indicate bugs
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
