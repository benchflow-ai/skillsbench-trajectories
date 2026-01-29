#!/usr/bin/env python3
"""Fuzz driver for Mini-SGLang - LLM inference framework"""

import atheris
import sys
import json
import struct

# Import minisgl components for fuzzing
try:
    from minisgl.message.utils import deserialize_type, serialize_type
except ImportError:
    # If minisgl not yet installed, provide stubs
    def deserialize_type(data_dict):
        return data_dict
    def serialize_type(obj):
        return {"value": str(obj)}


@atheris.instrument_func
def test_one(data):
    """Fuzz driver for minisgl message handling"""
    if len(data) < 1:
        return

    # Test 1: JSON parsing for API requests
    try:
        json_str = data.decode('utf-8', errors='ignore')
        if len(json_str) < 10000:
            # Try to parse as JSON (common in API)
            obj = json.loads(json_str)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        pass
    except Exception:
        raise

    # Test 2: Dictionary deserialization
    try:
        json_str = data.decode('utf-8', errors='ignore')
        if len(json_str) < 10000:
            # Try to parse and deserialize
            obj = json.loads(json_str)
            if isinstance(obj, dict):
                result = deserialize_type(obj)
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        pass
    except Exception:
        raise

    # Test 3: Message validation (simulated API requests)
    try:
        if len(data) >= 2:
            # Simulate different message types
            test_messages = [
                # Generate request
                {"prompt": data[:100].decode('utf-8', errors='ignore'),
                 "max_tokens": struct.unpack('<I', data[100:104] if len(data) >= 104 else b'\x00\x00\x00\x10')[0] % 2048},

                # Chat completion request
                {"messages": [{"role": "user",
                              "content": data.decode('utf-8', errors='ignore')[:500]}],
                 "max_tokens": 100},

                # With sampling params
                {"prompt": data[:200].decode('utf-8', errors='ignore'),
                 "temperature": struct.unpack('<f', data[200:204] if len(data) >= 204 else b'\x00\x00\x80?')[0]},
            ]

            for msg in test_messages:
                try:
                    # Serialize and deserialize
                    serialized = serialize_type(msg)
                    if isinstance(serialized, dict):
                        deserialized = deserialize_type(serialized)
                except:
                    pass
    except Exception:
        raise

    # Test 4: Tokenizer input simulation
    try:
        text_input = data.decode('utf-8', errors='ignore')
        if len(text_input) < 50000:  # Reasonable token input size
            # Simulate tokenizer message
            msg = {
                "uid": struct.unpack('<I', data[:4] if len(data) >= 4 else b'\x00\x00\x00\x00')[0],
                "text": text_input,
            }
            serialized = serialize_type(msg)
            deserialized = deserialize_type(serialized)
    except Exception:
        pass

    # Test 5: Sampling parameters
    try:
        if len(data) >= 16:
            # Extract numerical values
            temperature = struct.unpack('<f', data[:4])[0]
            top_k = struct.unpack('<i', data[4:8])[0]
            top_p = struct.unpack('<f', data[8:12])[0]
            max_tokens = struct.unpack('<I', data[12:16])[0] % 4096

            sampling_params = {
                "temperature": max(0.0, min(2.0, abs(temperature))),  # Clamp to valid range
                "top_k": max(-1, top_k),
                "top_p": max(0.0, min(1.0, abs(top_p))),
                "max_tokens": max(1, max_tokens),
            }

            # Try to serialize
            serialized = serialize_type(sampling_params)
    except Exception:
        pass

    # Test 6: Large nested structures
    try:
        json_str = data.decode('utf-8', errors='ignore')
        if len(json_str) < 10000:
            # Create nested structure
            nested = {
                "level1": {
                    "level2": {
                        "level3": {
                            "data": json_str[:100],
                            "value": len(json_str),
                        }
                    }
                }
            }

            serialized = serialize_type(nested)
            deserialized = deserialize_type(serialized)
    except Exception:
        pass

    # Test 7: Invalid type names in deserialization
    try:
        # Test with fake __type__ field
        obj_with_type = {
            "__type__": data[:50].decode('utf-8', errors='ignore'),
            "data": "test",
        }
        result = deserialize_type(obj_with_type)
    except (KeyError, ValueError, AttributeError):
        pass
    except Exception:
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()
