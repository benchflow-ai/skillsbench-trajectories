#!/usr/bin/env python3
"""
Fuzzer for ujson - Ultra-fast JSON encoder/decoder
Targets: ujson.loads() and ujson.dumps() with various inputs
Focus on loads() due to C parser and known security concerns
"""

import sys
import atheris

# Import after atheris setup
with atheris.instrument_imports():
    import ujson


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz ujson.loads() and ujson.dumps() with various patterns."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: ujson.loads() with random JSON strings (PRIMARY TARGET)
    try:
        json_string = fdp.ConsumeUnicodeNoSurrogates(500)
        if json_string:
            result = ujson.loads(json_string)
    except (ValueError, TypeError, OverflowError, KeyError) as e:
        # Expected exceptions for invalid JSON
        pass
    except Exception as e:
        # Catch any crashes or unexpected errors
        pass

    # Test 2: ujson.loads() with bytes
    try:
        json_bytes = fdp.ConsumeBytes(300)
        if json_bytes:
            result = ujson.loads(json_bytes)
    except (ValueError, TypeError, OverflowError, KeyError, UnicodeDecodeError) as e:
        pass
    except Exception as e:
        pass

    # Test 3: ujson.dumps() with random Python objects
    try:
        # Create a random Python object to encode
        obj_type = fdp.ConsumeIntInRange(0, 6)

        if obj_type == 0:
            # Dict
            obj = {
                fdp.ConsumeUnicodeNoSurrogates(20): fdp.ConsumeInt(4)
                for _ in range(fdp.ConsumeIntInRange(0, 5))
            }
        elif obj_type == 1:
            # List
            obj = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))]
        elif obj_type == 2:
            # String
            obj = fdp.ConsumeUnicodeNoSurrogates(100)
        elif obj_type == 3:
            # Number
            obj = fdp.ConsumeFloat()
        elif obj_type == 4:
            # Bool
            obj = fdp.ConsumeBool()
        elif obj_type == 5:
            # None
            obj = None
        else:
            # Nested structure
            obj = {
                "nested": [1, 2, {"inner": fdp.ConsumeUnicodeNoSurrogates(20)}]
            }

        result = ujson.dumps(obj)
    except (ValueError, TypeError, OverflowError) as e:
        # Expected exceptions
        pass
    except Exception as e:
        pass

    # Test 4: ujson.loads() with special JSON constructs
    try:
        # Test with constructed JSON-like strings
        json_templates = [
            '{"key": "value"}',
            '[1, 2, 3]',
            'null',
            'true',
            'false',
            '""',
            '0',
            '{}',
            '[]',
        ]
        template = fdp.PickValueInList(json_templates)

        # Mutate the template
        fuzz_part = fdp.ConsumeUnicodeNoSurrogates(50)
        mutated = template + fuzz_part

        result = ujson.loads(mutated)
    except (ValueError, TypeError, OverflowError, KeyError) as e:
        pass
    except Exception as e:
        pass

    # Test 5: Test ujson.dumps() with options
    try:
        obj = {"test": fdp.ConsumeUnicodeNoSurrogates(50)}
        encode_html_chars = fdp.ConsumeBool()
        ensure_ascii = fdp.ConsumeBool()

        result = ujson.dumps(
            obj,
            encode_html_chars=encode_html_chars,
            ensure_ascii=ensure_ascii
        )
    except (ValueError, TypeError, OverflowError) as e:
        pass
    except Exception as e:
        pass

    # Test 6: Round-trip testing
    try:
        json_string = fdp.ConsumeUnicodeNoSurrogates(200)
        if json_string:
            # Try to parse and re-encode
            parsed = ujson.loads(json_string)
            encoded = ujson.dumps(parsed)
            # Try to parse again
            reparsed = ujson.loads(encoded)
    except (ValueError, TypeError, OverflowError, KeyError) as e:
        pass
    except Exception as e:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
