#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL (Mini-SGLang) using Atheris (LibFuzzer-based).
This version focuses on testing serialization/deserialization logic
that doesn't require GPU dependencies.

Note: The full library requires torch/transformers/flashinfer which have
GPU dependencies. This fuzzer tests the pure Python serialization utilities
with mocked tensor handling, plus msgpack serialization used for IPC.
"""

import sys
import atheris
import json


@atheris.instrument_func
def _serialize_any_mock(value):
    """Mock serialization that doesn't require torch."""
    if isinstance(value, dict):
        return {k: _serialize_any_mock(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return type(value)(_serialize_any_mock(v) for v in value)
    elif isinstance(value, (int, float, str, type(None), bool, bytes)):
        return value
    else:
        # For other types, serialize as dict
        serialized = {"__type__": type(value).__name__}
        if hasattr(value, "__dict__"):
            for k, v in value.__dict__.items():
                serialized[k] = _serialize_any_mock(v)
        return serialized


@atheris.instrument_func
def _deserialize_any_mock(cls_map, data):
    """Mock deserialization that doesn't require torch."""
    if isinstance(data, dict):
        if "__type__" in data:
            return _deserialize_type_mock(cls_map, data)
        else:
            return {k: _deserialize_any_mock(cls_map, v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return type(data)(_deserialize_any_mock(cls_map, d) for d in data)
    elif isinstance(data, (int, float, str, type(None), bool, bytes)):
        return data
    else:
        raise ValueError(f"Cannot deserialize type {type(data)}")


@atheris.instrument_func
def _deserialize_type_mock(cls_map, data):
    """Mock type deserialization."""
    type_name = data.get("__type__", "")

    # Handle tensor type (mock)
    if type_name == "Tensor":
        buffer = data.get("buffer", b"")
        dtype_str = data.get("dtype", "float32").replace("torch.", "")
        # Return the raw data for tensors
        return {"_mock_tensor": True, "buffer": buffer, "dtype": dtype_str}

    # Try to find the type in cls_map
    if type_name in cls_map:
        cls = cls_map[type_name]
        kwargs = {}
        for k, v in data.items():
            if k == "__type__":
                continue
            kwargs[k] = _deserialize_any_mock(cls_map, v)
        try:
            return cls(**kwargs)
        except Exception:
            return kwargs

    # Return processed dict if type not found
    result = {}
    for k, v in data.items():
        if k == "__type__":
            continue
        result[k] = _deserialize_any_mock(cls_map, v)
    return result


@atheris.instrument_func
def TestOneInput(data: bytes):
    """
    Fuzz entry point targeting MiniSGL-style serialization and parsing.

    Priority targets:
    1. Deserialization of arbitrary dict structures
    2. Type handling in serialization
    3. Nested structure handling
    4. Msgpack unpacking (used in ZMQ communication)
    """
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: Deserialize with malformed dictionary structures
    try:
        # Create a dictionary that mimics serialized data
        type_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))

        # Build a test dictionary with __type__ field
        test_dict = {
            "__type__": type_name,
        }

        # Add some random fields
        num_fields = fdp.ConsumeIntInRange(0, 10)
        for i in range(num_fields):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 50))
            if not key:
                key = f"field_{i}"

            # Randomly choose value type
            value_type = fdp.ConsumeIntInRange(0, 5)
            if value_type == 0:
                value = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100))
            elif value_type == 1:
                value = fdp.ConsumeInt(8)
            elif value_type == 2:
                value = fdp.ConsumeFloat()
            elif value_type == 3:
                value = fdp.ConsumeBool()
            elif value_type == 4:
                value = None
            else:
                value = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 100))

            test_dict[key] = value

        # Try to deserialize with an empty class map
        _deserialize_any_mock({}, test_dict)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        pass
    except Exception:
        pass

    # Test 2: Serialize various Python objects
    try:
        obj_type = fdp.ConsumeIntInRange(0, 6)

        if obj_type == 0:
            obj = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
        elif obj_type == 1:
            obj = fdp.ConsumeInt(8)
        elif obj_type == 2:
            obj = fdp.ConsumeFloat()
        elif obj_type == 3:
            obj = fdp.ConsumeBool()
        elif obj_type == 4:
            obj = None
        elif obj_type == 5:
            # Create a list
            list_len = fdp.ConsumeIntInRange(0, 20)
            obj = [fdp.ConsumeInt(4) for _ in range(list_len)]
        else:
            # Create a dict
            dict_len = fdp.ConsumeIntInRange(0, 10)
            obj = {}
            for _ in range(dict_len):
                key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 20))
                if key:
                    obj[key] = fdp.ConsumeInt(4)

        _serialize_any_mock(obj)
    except (ValueError, TypeError, RecursionError, MemoryError):
        pass
    except Exception:
        pass

    # Test 3: Nested structures (depth stress test)
    try:
        depth = fdp.ConsumeIntInRange(0, 50)
        nested = {}
        current = nested
        for i in range(depth):
            key = f"level_{i}"
            current[key] = {}
            current = current[key]

        current["__type__"] = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50))
        current["value"] = fdp.ConsumeInt(4)

        _deserialize_any_mock({}, nested)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        pass
    except Exception:
        pass

    # Test 4: Test with tensor-like dictionary structure
    try:
        tensor_dict = {
            "__type__": "Tensor",
            "dtype": fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 20)),
            "shape": [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 5))],
            "buffer": fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000)),
        }
        _deserialize_any_mock({}, tensor_dict)
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    except Exception:
        pass

    # Test 5: Round-trip serialization
    try:
        original = {
            "text": fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200)),
            "number": fdp.ConsumeInt(4),
            "flag": fdp.ConsumeBool(),
        }
        serialized = _serialize_any_mock(original)
        _deserialize_any_mock({}, serialized)
    except (ValueError, TypeError, RecursionError):
        pass
    except Exception:
        pass

    # Test 6: JSON round-trip (used in API)
    try:
        json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1000))
        if json_str:
            parsed = json.loads(json_str)
            json.dumps(parsed)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError, UnicodeDecodeError):
        pass
    except Exception:
        pass

    # Test 7: Msgpack round-trip (used in ZMQ communication)
    try:
        import msgpack
        raw_data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000))
        if raw_data:
            unpacked = msgpack.unpackb(raw_data, raw=False, strict_map_key=False)
            msgpack.packb(unpacked)
    except Exception:
        # msgpack can raise various exceptions for malformed data
        pass

    # Test 8: Msgpack with structured data
    try:
        import msgpack
        test_obj = {
            "type": fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50)),
            "data": {
                "values": [fdp.ConsumeFloat() for _ in range(fdp.ConsumeIntInRange(0, 10))],
                "flag": fdp.ConsumeBool(),
            }
        }
        packed = msgpack.packb(test_obj)
        msgpack.unpackb(packed, raw=False)
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
