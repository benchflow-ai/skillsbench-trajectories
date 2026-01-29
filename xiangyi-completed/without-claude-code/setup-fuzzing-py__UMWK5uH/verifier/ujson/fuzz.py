#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for UltraJSON (ujson) library.
Uses atheris for coverage-guided fuzzing.

Note: ujson is a C extension, so Python-based coverage instrumentation
won't track the internal C code. This fuzzer is still useful for finding
crashes and bugs in the C implementation.
"""
import sys

# Pre-import ujson before atheris to avoid slow instrumented import
import ujson

import atheris


@atheris.instrument_func
def TestOneInput(data: bytes):
    """Fuzz target for ujson library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz ujson.loads() with string input
            json_str = fdp.ConsumeUnicodeNoSurrogates(2048)
            ujson.loads(json_str)

        elif choice == 1:
            # Fuzz ujson.loads() with bytes input
            json_bytes = fdp.ConsumeBytes(2048)
            ujson.loads(json_bytes)

        elif choice == 2:
            # Fuzz ujson.dumps() with constructed objects
            def build_object(fdp, depth=0):
                if depth > 8 or fdp.remaining_bytes() < 4:
                    prim_type = fdp.ConsumeIntInRange(0, 4)
                    if prim_type == 0:
                        return fdp.ConsumeInt(8)
                    elif prim_type == 1:
                        return fdp.ConsumeFloat()
                    elif prim_type == 2:
                        return fdp.ConsumeUnicodeNoSurrogates(32)
                    elif prim_type == 3:
                        return fdp.ConsumeBool()
                    else:
                        return None

                struct_type = fdp.ConsumeIntInRange(0, 2)
                if struct_type == 0:
                    result = {}
                    num_items = fdp.ConsumeIntInRange(0, 4)
                    for _ in range(num_items):
                        key = fdp.ConsumeUnicodeNoSurrogates(8)
                        result[key] = build_object(fdp, depth + 1)
                    return result
                elif struct_type == 1:
                    result = []
                    num_items = fdp.ConsumeIntInRange(0, 4)
                    for _ in range(num_items):
                        result.append(build_object(fdp, depth + 1))
                    return result
                else:
                    return fdp.ConsumeUnicodeNoSurrogates(32)

            obj = build_object(fdp)

            ensure_ascii = fdp.ConsumeBool()
            encode_html_chars = fdp.ConsumeBool()
            escape_forward_slashes = fdp.ConsumeBool()
            sort_keys = fdp.ConsumeBool()
            indent = fdp.ConsumeIntInRange(0, 4)
            allow_nan = fdp.ConsumeBool()

            result = ujson.dumps(
                obj,
                ensure_ascii=ensure_ascii,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                sort_keys=sort_keys,
                indent=indent,
                allow_nan=allow_nan,
            )

            # Verify round-trip
            ujson.loads(result)

        elif choice == 3:
            # Fuzz with special values (NaN, Infinity)
            special_values = [
                float('nan'),
                float('inf'),
                float('-inf'),
                0.0,
                -0.0,
                1e308,
                -1e308,
                1e-308,
                2147483647,
                -2147483648,
            ]

            value = fdp.PickValueInList(special_values)
            obj = {"value": value}

            allow_nan = fdp.ConsumeBool()
            result = ujson.dumps(obj, allow_nan=allow_nan)
            if allow_nan:
                ujson.loads(result)

    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
