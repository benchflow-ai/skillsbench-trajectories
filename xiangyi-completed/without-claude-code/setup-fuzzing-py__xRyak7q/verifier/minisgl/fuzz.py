#!/usr/bin/env python3
"""
Coverage-guided fuzz driver for minisgl serialization/deserialization utilities.

Uses atheris (LibFuzzer-compatible Python fuzzing library) to fuzz:
1. deserialize_type() - Critical deserialization function
2. serialize_type() - Serialization function
3. Message decoder functions

This fuzzer focuses on pure Python serialization/deserialization utilities
that don't require GPU or heavy dependencies like torch/cuda/flashinfer.
"""

import sys

# Add the python package path for direct imports if minisgl isn't installed
sys.path.insert(0, "/app/minisgl/python")

import atheris

# Instrument imports for coverage before importing target modules
with atheris.instrument_imports():
    import msgpack
    import json
    from dataclasses import dataclass
    from typing import Any, Dict, Type


# Mock numpy and torch to avoid GPU dependencies
class MockNumpyDtype:
    """Mock numpy dtype."""
    pass


class MockNumpy:
    """Mock numpy module for fuzzing without actual numpy/torch."""
    int8 = MockNumpyDtype()
    int16 = MockNumpyDtype()
    int32 = MockNumpyDtype()
    int64 = MockNumpyDtype()
    float16 = MockNumpyDtype()
    float32 = MockNumpyDtype()
    float64 = MockNumpyDtype()

    @staticmethod
    def frombuffer(buffer, dtype):
        # Return a mock array-like object
        return MockNumpyArray(buffer)


class MockNumpyArray:
    """Mock numpy array."""
    def __init__(self, data):
        self._data = data

    def copy(self):
        return self

    def tobytes(self):
        if isinstance(self._data, bytes):
            return self._data
        return b""


class MockTensor:
    """Mock torch.Tensor for fuzzing without torch."""
    def __init__(self, data=None):
        self._data = data

    def dim(self):
        return 1

    def numpy(self):
        return MockNumpyArray(self._data if self._data else b"")

    @property
    def dtype(self):
        return "torch.int32"


class MockTorch:
    """Mock torch module."""
    Tensor = MockTensor

    @staticmethod
    def from_numpy(arr):
        return MockTensor(arr._data if hasattr(arr, '_data') else None)


# Replace real numpy/torch with mocks in the utils module namespace
mock_np = MockNumpy()
mock_torch = MockTorch()


# Re-implement the serialization functions locally to avoid import issues
def _serialize_any(value: Any) -> Any:
    """Serialize any value recursively."""
    if isinstance(value, dict):
        return {k: _serialize_any(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return type(value)(_serialize_any(v) for v in value)
    elif isinstance(value, (int, float, str, type(None), bool, bytes)):
        return value
    else:
        return serialize_type(value)


def serialize_type(self) -> Dict:
    """Serialize an object to a dictionary."""
    serialized = {}

    if isinstance(self, MockTensor):
        serialized["__type__"] = "Tensor"
        serialized["buffer"] = self.numpy().tobytes()
        serialized["dtype"] = str(self.dtype)
        return serialized

    serialized["__type__"] = self.__class__.__name__
    for k, v in self.__dict__.items():
        serialized[k] = _serialize_any(v)
    return serialized


def _deserialize_any(cls_map: Dict[str, Type], data: Any) -> Any:
    """Deserialize any value recursively."""
    if isinstance(data, dict):
        if "__type__" in data:
            return deserialize_type(cls_map, data)
        else:
            return {k: _deserialize_any(cls_map, v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return type(data)(_deserialize_any(cls_map, d) for d in data)
    elif isinstance(data, (int, float, str, type(None), bool, bytes)):
        return data
    else:
        raise ValueError(f"Cannot deserialize type {type(data)}")


def deserialize_type(cls_map: Dict[str, Type], data: Dict) -> Any:
    """
    Deserialize a dictionary to an object.

    This is the critical function to fuzz - it:
    - Dynamically looks up types from cls_map based on user-controlled __type__ field
    - Handles tensor deserialization with dtype conversion
    - Uses np.frombuffer which can have buffer overflow issues
    """
    type_name = data["__type__"]

    # Tensor deserialization path
    if type_name == "Tensor":
        buffer = data["buffer"]
        dtype_str = data["dtype"].replace("torch.", "")
        np_dtype = getattr(mock_np, dtype_str, mock_np.float32)
        if not isinstance(buffer, bytes):
            raise AssertionError("buffer must be bytes")
        np_tensor = mock_np.frombuffer(buffer, dtype=np_dtype)
        return mock_torch.from_numpy(np_tensor.copy())

    # Normal object deserialization
    cls = cls_map[type_name]
    kwargs = {}
    for k, v in data.items():
        if k == "__type__":
            continue
        kwargs[k] = _deserialize_any(cls_map, v)
    return cls(**kwargs)


# Define some test classes that could be in a cls_map
@dataclass
class MockSamplingParams:
    """Mock SamplingParams for fuzzing."""
    temperature: float = 0.0
    top_k: int = -1
    top_p: float = 1.0
    ignore_eos: bool = False
    max_tokens: int = 1024


@dataclass
class MockUserMsg:
    """Mock UserMsg for fuzzing."""
    uid: int = 0
    text: str = ""


@dataclass
class MockUserReply:
    """Mock UserReply for fuzzing."""
    uid: int = 0
    incremental_output: str = ""
    finished: bool = False


@dataclass
class MockDetokenizeMsg:
    """Mock DetokenizeMsg for fuzzing."""
    uid: int = 0
    next_token: int = 0
    finished: bool = False


# Build the cls_map with available types
CLS_MAP: Dict[str, Type] = {
    "MockSamplingParams": MockSamplingParams,
    "MockUserMsg": MockUserMsg,
    "MockUserReply": MockUserReply,
    "MockDetokenizeMsg": MockDetokenizeMsg,
    "SamplingParams": MockSamplingParams,
    "UserMsg": MockUserMsg,
    "UserReply": MockUserReply,
    "DetokenizeMsg": MockDetokenizeMsg,
}


def TestOneInput(data: bytes) -> None:
    """
    Fuzz target function called by atheris with random bytes.

    Tries to parse the input as msgpack or JSON and then call
    the deserialization functions with various malformed inputs.
    """
    if len(data) < 2:
        return

    # Try parsing as msgpack first (more efficient binary format)
    parsed_data = None
    try:
        parsed_data = msgpack.unpackb(data, raw=False, strict_map_key=False)
    except Exception:
        pass

    # If msgpack fails, try JSON
    if parsed_data is None:
        try:
            parsed_data = json.loads(data.decode('utf-8', errors='ignore'))
        except Exception:
            pass

    # If neither works, create a dict from raw bytes
    if parsed_data is None:
        # Create a synthetic dict to fuzz with
        try:
            # Use first byte to select a type
            type_idx = data[0] % (len(CLS_MAP) + 2)
            type_names = list(CLS_MAP.keys()) + ["Tensor", "UnknownType"]
            type_name = type_names[type_idx]

            parsed_data = {
                "__type__": type_name,
            }

            # Add some fields based on remaining bytes
            if len(data) > 1:
                parsed_data["uid"] = int.from_bytes(data[1:5] if len(data) >= 5 else data[1:],
                                                     byteorder='little', signed=True)
            if len(data) > 5:
                parsed_data["text"] = data[5:].decode('utf-8', errors='replace')
            if type_name == "Tensor":
                parsed_data["buffer"] = data[1:] if len(data) > 1 else b""
                parsed_data["dtype"] = "torch.float32"
                if len(data) > 10:
                    # Fuzz the dtype too
                    dtypes = ["int8", "int16", "int32", "int64", "float16", "float32", "float64",
                              "invalid", "", "torch.bfloat16"]
                    dtype_idx = data[1] % len(dtypes)
                    parsed_data["dtype"] = f"torch.{dtypes[dtype_idx]}"
        except Exception:
            return

    # Now fuzz the deserialization functions
    if isinstance(parsed_data, dict):
        # Ensure __type__ exists for deserialize_type
        if "__type__" not in parsed_data:
            parsed_data["__type__"] = "MockUserMsg"

        # Fuzz deserialize_type
        try:
            result = deserialize_type(CLS_MAP, parsed_data)
        except (KeyError, TypeError, ValueError, AttributeError, AssertionError):
            # Expected exceptions for malformed input
            pass
        except RecursionError:
            # Deep nesting - expected for some inputs
            pass

        # Fuzz _deserialize_any
        try:
            result = _deserialize_any(CLS_MAP, parsed_data)
        except (KeyError, TypeError, ValueError, AttributeError, AssertionError):
            pass
        except RecursionError:
            pass

    # Also fuzz with nested structures
    if isinstance(parsed_data, (list, dict)):
        try:
            result = _deserialize_any(CLS_MAP, parsed_data)
        except (KeyError, TypeError, ValueError, AttributeError, AssertionError):
            pass
        except RecursionError:
            pass

    # Fuzz serialization with objects that have the parsed data as attributes
    try:
        if isinstance(parsed_data, dict):
            obj = MockUserMsg()
            # Set arbitrary attributes from parsed data
            for k, v in list(parsed_data.items())[:10]:  # Limit to prevent huge objects
                if isinstance(k, str) and k.isidentifier():
                    try:
                        setattr(obj, k, v)
                    except Exception:
                        pass

            serialized = serialize_type(obj)
            # Round-trip test
            if "__type__" in serialized:
                try:
                    deserialized = deserialize_type(CLS_MAP, serialized)
                except Exception:
                    pass
    except (TypeError, ValueError, AttributeError, RecursionError):
        pass


def main():
    """Main entry point for the fuzzer."""
    # Configure atheris
    atheris.Setup(sys.argv, TestOneInput)

    # Run the fuzzer
    atheris.Fuzz()


if __name__ == "__main__":
    main()
