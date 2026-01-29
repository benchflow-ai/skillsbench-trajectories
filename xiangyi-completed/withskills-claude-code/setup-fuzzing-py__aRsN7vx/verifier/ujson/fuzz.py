#!/usr/bin/env python3
"""
Fuzz driver for ujson (UltraJSON) library.
Targets the JSON parsing and encoding functions with various inputs.
Focus on finding memory safety issues in the native C extension.
"""

import sys
import atheris

# Note: ujson is a C extension, so we don't instrument it
# We instrument the harness itself to get coverage feedback
@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for ujson functions."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Import ujson here (not instrumented since it's native code)
    import ujson

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz ujson.loads() with string input
            json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))

            try:
                result = ujson.loads(json_string)
            except (ujson.JSONDecodeError, ValueError, OverflowError):
                pass  # Expected exceptions

        elif choice == 1:
            # Fuzz ujson.loads() with bytes input
            json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000))

            try:
                result = ujson.loads(json_bytes)
            except (ujson.JSONDecodeError, ValueError, OverflowError, UnicodeDecodeError):
                pass  # Expected exceptions

        elif choice == 2:
            # Fuzz ujson.dumps() with generated objects
            # Build a random JSON-serializable object
            obj = generate_json_object(fdp)

            # Generate random options
            ensure_ascii = fdp.ConsumeBool()
            indent = fdp.ConsumeIntInRange(0, 10) if fdp.ConsumeBool() else 0
            encode_html_chars = fdp.ConsumeBool()
            escape_forward_slashes = fdp.ConsumeBool()
            sort_keys = fdp.ConsumeBool()

            try:
                result = ujson.dumps(
                    obj,
                    ensure_ascii=ensure_ascii,
                    indent=indent,
                    encode_html_chars=encode_html_chars,
                    escape_forward_slashes=escape_forward_slashes,
                    sort_keys=sort_keys
                )
            except (ValueError, OverflowError, TypeError):
                pass  # Expected exceptions

    except Exception as e:
        # Catch any unexpected exceptions
        exception_type = type(e).__name__
        safe_exceptions = [
            'JSONDecodeError', 'ValueError', 'OverflowError', 'TypeError',
            'UnicodeDecodeError', 'RecursionError', 'MemoryError'
        ]
        if exception_type not in safe_exceptions:
            raise  # Re-raise unexpected exceptions


def generate_json_object(fdp, depth=0, max_depth=5):
    """Generate a random JSON-serializable object."""
    if depth >= max_depth:
        # Return simple value at max depth
        return generate_simple_value(fdp)

    choice = fdp.ConsumeIntInRange(0, 5)

    if choice == 0:
        # null
        return None
    elif choice == 1:
        # boolean
        return fdp.ConsumeBool()
    elif choice == 2:
        # number
        if fdp.ConsumeBool():
            return fdp.ConsumeInt(8)
        else:
            return fdp.ConsumeRegularFloat()
    elif choice == 3:
        # string
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
    elif choice == 4:
        # array
        size = fdp.ConsumeIntInRange(0, 5)
        return [generate_json_object(fdp, depth + 1, max_depth) for _ in range(size)]
    elif choice == 5:
        # object
        size = fdp.ConsumeIntInRange(0, 5)
        obj = {}
        for _ in range(size):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 20))
            value = generate_json_object(fdp, depth + 1, max_depth)
            obj[key] = value
        return obj


def generate_simple_value(fdp):
    """Generate a simple JSON value (no nesting)."""
    choice = fdp.ConsumeIntInRange(0, 3)
    if choice == 0:
        return None
    elif choice == 1:
        return fdp.ConsumeBool()
    elif choice == 2:
        return fdp.ConsumeInt(4)
    else:
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 20))


def main():
    """Main entry point for fuzzing."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
