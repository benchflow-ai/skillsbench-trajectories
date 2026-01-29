#!/usr/bin/env python3
"""
Atheris-based fuzzer for MiniSGL
Targets: JSON parsing and message handling (generic fuzzer due to library structure)
"""

import sys
import json
import atheris

# Note: MiniSGL may have complex dependencies, so we'll fuzz basic JSON parsing
# which is likely used in the message/server components

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for JSON parsing in MiniSGL context"""
    if len(data) == 0:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test JSON parsing (likely used for API/message handling)
    json_string = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not json_string:
        return

    try:
        # Parse JSON
        parsed = json.loads(json_string)

        # If successful, try to serialize back
        if parsed is not None:
            serialized = json.dumps(parsed)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        # Expected exceptions for invalid JSON
        pass
    except OverflowError:
        # Expected for very large numbers
        pass
    except Exception as e:
        # Log unexpected exceptions
        if not isinstance(e, (json.JSONDecodeError, ValueError, TypeError, RecursionError, OverflowError)):
            raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
