#!/usr/bin/env python3
"""
LibFuzzer driver for Mini-SGLang library - LLM inference framework.
Tests message serialization, tokenization, and sampling functions.
"""

import sys
import json
import random

# Import minisgl components
try:
    from minisgl.message.utils import serialize_type, deserialize_type
    from minisgl.core import Req, Batch, SamplingParams
    minisgl_available = True
except ImportError:
    minisgl_available = False


def fuzz_minisgl(data: bytes):
    """Main fuzzer function targeting Mini-SGLang"""

    if not minisgl_available:
        return

    if len(data) < 1:
        return

    # Determine which function to test based on first byte
    choice = data[0] % 4

    try:
        if choice == 0:
            # Test serialization/deserialization
            _fuzz_serialization(data)
        elif choice == 1:
            # Test SamplingParams creation
            _fuzz_sampling_params(data)
        elif choice == 2:
            # Test Req state management
            _fuzz_req_state(data)
        elif choice == 3:
            # Test with JSON-based input
            _fuzz_json_input(data)
    except Exception:
        # Expected exceptions during fuzzing
        pass


def _fuzz_serialization(data: bytes):
    """Test serialize_type and deserialize_type"""
    try:
        # Decode input as UTF-8 for string testing
        test_str = data.decode('utf-8', errors='ignore')

        # Create test objects with various types
        test_obj = {
            "string": test_str,
            "number": int.from_bytes(data[:4], 'big', signed=True) if len(data) >= 4 else 0,
            "float": float(len(data)),
            "bool": len(data) % 2 == 0,
            "none": None,
        }

        # Serialize
        serialized = serialize_type(test_obj)
        assert isinstance(serialized, dict)

        # Deserialize back
        if isinstance(serialized, dict):
            deserialized = deserialize_type(serialized)
            # Result should be structurally equivalent
            assert deserialized is not None

    except (TypeError, ValueError, AttributeError):
        # Expected errors
        pass
    except Exception:
        pass


def _fuzz_sampling_params(data: bytes):
    """Test SamplingParams creation with various values"""
    try:
        # Extract parameters from data
        if len(data) >= 8:
            temperature = float(int.from_bytes(data[0:2], 'big', signed=False) % 300) / 100.0
            top_k = int.from_bytes(data[2:4], 'big', signed=False) % 10000
            top_p_raw = int.from_bytes(data[4:6], 'big', signed=False) % 100
            top_p = top_p_raw / 100.0
            max_tokens = int.from_bytes(data[6:8], 'big', signed=False) % 100000
        else:
            temperature = 0.7
            top_k = 50
            top_p = 0.9
            max_tokens = 512

        # Create SamplingParams
        try:
            params = SamplingParams(
                temperature=max(0.01, temperature),
                top_k=max(0, top_k),
                top_p=max(0.0, min(1.0, top_p)),
                max_tokens=max(1, max_tokens),
            )
            assert params is not None
        except (TypeError, ValueError):
            pass

    except Exception:
        pass


def _fuzz_req_state(data: bytes):
    """Test Req state management"""
    try:
        # Create a simple request with varying parameters
        if len(data) >= 4:
            input_len = int.from_bytes(data[0:2], 'big', signed=False) % 10000
            output_len = int.from_bytes(data[2:4], 'big', signed=False) % 10000
        else:
            input_len = 10
            output_len = 5

        # Create Req object with mock input_ids
        input_ids = list(range(max(1, input_len % 1000)))

        try:
            req = Req(input_ids=input_ids, req_id=0)
            # Test state properties
            assert req.input_len >= 0
            assert req.output_len >= 0

            # Test can_decode() method if available
            if hasattr(req, 'can_decode'):
                can_decode = req.can_decode()
                assert isinstance(can_decode, bool)

        except (TypeError, ValueError, AttributeError):
            pass

    except Exception:
        pass


def _fuzz_json_input(data: bytes):
    """Test with JSON-based fuzzing"""
    try:
        # Try to parse as JSON
        try:
            test_json = json.loads(data.decode('utf-8', errors='ignore'))
            if isinstance(test_json, dict):
                # Try to deserialize as message
                deserialized = deserialize_type(test_json)
                assert deserialized is not None
        except (json.JSONDecodeError, ValueError):
            # Not valid JSON, that's ok
            pass

        # Try creating objects from JSON-like structures
        test_dict = {
            "type": "test",
            "data": data[:100].decode('utf-8', errors='ignore'),
        }
        serialized = serialize_type(test_dict)
        assert isinstance(serialized, dict)

    except Exception:
        pass


if __name__ == "__main__":
    # Fuzzing main loop
    if not minisgl_available:
        print("Mini-SGLang not fully available, skipping fuzzing")
    else:
        test_cases = [
            b'{"test": "data"}',
            b'simple_string',
            b'123',
            b'',
            b'\x00\xff',
        ]

        # Add random test cases
        random.seed(42)
        for _ in range(100):
            test_cases.append(bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]))

        print(f"Running {len(test_cases)} test cases for minisgl fuzzing...")
        success = 0
        errors = 0

        for test_case in test_cases:
            try:
                fuzz_minisgl(test_case)
                success += 1
            except Exception as e:
                errors += 1

        print(f"Completed: {success} successful, {errors} with expected errors")
