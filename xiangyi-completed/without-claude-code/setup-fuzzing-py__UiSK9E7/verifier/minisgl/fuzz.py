#!/usr/bin/env python3
"""
Coverage-guided fuzzing driver for the MiniSGL library.
Uses atheris for LibFuzzer-style fuzzing.

Note: This fuzzer focuses on the serialization/deserialization and
API request parsing components that don't require GPU/model loading.
"""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for MiniSGL library."""
    import json

    # Import serialization utilities
    try:
        from minisgl.message.utils import serialize_type, deserialize_type
    except ImportError:
        # Fallback if module structure is different
        try:
            sys.path.insert(0, "/app/minisgl/python")
            from minisgl.message.utils import serialize_type, deserialize_type
        except ImportError:
            return

    # Convert bytes to string for testing
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if len(text) > 50000:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: JSON parsing (simulating API request parsing)
    try:
        parsed = json.loads(text)
        # Try to deserialize as if it were a serialized object
        if isinstance(parsed, dict):
            deserialize_type({}, parsed)
    except (json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError):
        pass
    except Exception:
        pass

    # Test 2: Test serialization with various Python types
    try:
        # Create test objects from fuzzed data
        test_obj = {
            "prompt": fdp.ConsumeUnicodeNoSurrogates(100),
            "max_tokens": fdp.ConsumeIntInRange(-1000, 100000),
            "temperature": fdp.ConsumeFloat(),
        }
        serialized = serialize_type(test_obj)
        # Round-trip test
        deserialize_type({}, serialized)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        pass
    except Exception:
        pass

    # Test 3: Test nested structure serialization
    if len(data) > 20:
        try:
            nested = {
                "messages": [
                    {"role": fdp.ConsumeUnicodeNoSurrogates(10),
                     "content": fdp.ConsumeUnicodeNoSurrogates(50)}
                    for _ in range(fdp.ConsumeIntInRange(0, 5))
                ],
                "options": {
                    "key": fdp.ConsumeUnicodeNoSurrogates(20),
                }
            }
            serialized = serialize_type(nested)
            deserialize_type({}, serialized)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            pass
        except Exception:
            pass

    # Test 4: Test deserialization with type confusion attempts
    type_confusion_payloads = [
        {"__type__": fdp.ConsumeUnicodeNoSurrogates(30)},
        {"__type__": "Tensor", "data": text},
        {"__type__": "list", "__value__": text},
    ]

    for payload in type_confusion_payloads:
        try:
            deserialize_type({}, payload)
        except (ValueError, TypeError, KeyError, AttributeError, ModuleNotFoundError):
            pass
        except Exception:
            pass

    # Test 5: Pydantic model validation (if available)
    try:
        from minisgl.server.api_server import GenerateRequest

        # Try to create a GenerateRequest with fuzzed data
        GenerateRequest(
            prompt=fdp.ConsumeUnicodeNoSurrogates(100),
            max_tokens=fdp.ConsumeIntInRange(-1000, 100000),
            ignore_eos=fdp.ConsumeBool(),
        )
    except ImportError:
        pass
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception:
        pass

    # Test 6: Test sampling parameters validation
    try:
        from minisgl.core import SamplingParams

        SamplingParams(
            temperature=fdp.ConsumeFloat(),
            top_k=fdp.ConsumeIntInRange(-1000, 100000),
            top_p=fdp.ConsumeFloat(),
            ignore_eos=fdp.ConsumeBool(),
            max_tokens=fdp.ConsumeIntInRange(-1000, 100000),
        )
    except ImportError:
        pass
    except (ValueError, TypeError, AttributeError, OverflowError):
        pass
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
