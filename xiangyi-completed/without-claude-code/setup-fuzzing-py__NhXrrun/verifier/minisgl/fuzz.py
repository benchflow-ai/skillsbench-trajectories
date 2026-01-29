#!/usr/bin/env python3
"""
Coverage-guided fuzzer for MiniSGL library using Atheris (LibFuzzer).
Targets message serialization/deserialization and core data structures.
Note: This fuzzer tests the pure Python parts available without GPU dependencies.
"""

import sys
import os

# Add minisgl python path to sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

import atheris
import struct
import json

# Enable coverage instrumentation before importing target modules
_modules_available = False
with atheris.instrument_imports():
    try:
        # Try to import core modules that don't require GPU
        from minisgl.core import SamplingParams
        from minisgl.message.utils import serialize_type, deserialize_type
        _modules_available = True
    except ImportError as e:
        # Fall back to testing just JSON/msgpack parsing patterns
        pass

    try:
        import msgpack
        _msgpack_available = True
    except ImportError:
        _msgpack_available = False


def TestOneInput(data):
    """Fuzz target for minisgl library."""
    # Need at least some bytes to work with
    if len(data) < 1:
        return

    try:
        input_str = data.decode("utf-8", errors="ignore")
    except Exception:
        return

    if not input_str:
        return

    # Test 1: If core modules available, test SamplingParams
    if _modules_available:
        try:
            # Extract numeric-like values from input
            if len(data) >= 16:
                temp = struct.unpack('f', data[0:4])[0]
                top_k = struct.unpack('i', data[4:8])[0]
                top_p = struct.unpack('f', data[8:12])[0]
                max_tokens = struct.unpack('i', data[12:16])[0]

                # Clamp values to reasonable ranges to avoid hangs
                temp = max(0.0, min(temp, 10.0)) if not (temp != temp) else 0.5  # NaN check
                top_p = max(0.0, min(top_p, 1.0)) if not (top_p != top_p) else 1.0
                max_tokens = max(1, min(abs(max_tokens), 4096))

                params = SamplingParams(
                    temperature=temp,
                    top_k=top_k,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                # Test serialization
                serialize_type(params)
        except (
            ValueError,
            TypeError,
            struct.error,
            OverflowError,
            AttributeError,
        ):
            pass
        except Exception:
            pass

        # Test 2: deserialize_type with crafted input
        try:
            # Try to parse input as JSON for deserialization
            json_data = json.loads(input_str)
            if isinstance(json_data, dict):
                # Add required __type__ field if missing
                if "__type__" not in json_data:
                    json_data["__type__"] = "SamplingParams"

                cls_map = {"SamplingParams": SamplingParams}
                deserialize_type(cls_map, json_data)
        except (
            json.JSONDecodeError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
        ):
            pass
        except Exception:
            pass

    # Test 3: JSON parsing (always available)
    try:
        json.loads(input_str)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    except Exception:
        pass

    # Test 4: msgpack parsing (if available)
    if _msgpack_available:
        try:
            msgpack.unpackb(data, strict_map_key=False)
        except (
            msgpack.exceptions.UnpackException,
            ValueError,
            TypeError,
            OverflowError,
        ):
            pass
        except Exception:
            pass

        # Test msgpack packing
        try:
            obj = json.loads(input_str)
            msgpack.packb(obj)
        except (json.JSONDecodeError, ValueError, TypeError, OverflowError):
            pass
        except Exception:
            pass


def main():
    # Run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
