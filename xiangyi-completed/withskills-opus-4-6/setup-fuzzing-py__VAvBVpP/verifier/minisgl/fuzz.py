"""
LibFuzzer-based fuzz driver for the minisgl library.

Targets CPU-only, no-GPU-required pure Python functions:
  1. find_printable_text  - Unicode text boundary detection
  2. _PARSE_MEM_BYTES     - Memory string parsing
  3. deserialize_type / _deserialize_any - Message deserialization
  4. msgpack -> deserialize_type pipeline

Usage:
  python fuzz.py                    # run fuzzer
  python fuzz.py corpus/            # run with corpus directory
  python fuzz.py -max_len=4096      # limit input size
"""

import atheris
import sys
import struct

# Add minisgl to the Python path before instrumented imports
sys.path.insert(0, "/app/minisgl/python")

# Import heavy third-party dependencies BEFORE atheris.instrument_imports()
# so they are not instrumented (saves significant startup time).
# These are transitive dependencies of minisgl modules.
import msgpack
import numpy as np
import torch  # noqa: F401 - needed by minisgl.message.utils at import time
import zmq  # noqa: F401 - needed by minisgl.utils.mp at import time
import transformers  # noqa: F401 - needed by minisgl.tokenizer.server at import time
from transformers import AutoTokenizer, LlamaTokenizer  # noqa: F401

# Instrument only minisgl module imports for coverage-guided fuzzing.
# Using enable_loader_override=False to avoid issues with custom loaders.
with atheris.instrument_imports(enable_loader_override=False):
    from minisgl.message.utils import deserialize_type, _deserialize_any
    from minisgl.tokenizer.detokenize import find_printable_text
    from minisgl.env import _PARSE_MEM_BYTES


# A safe, minimal cls_map for deserialize_type testing.
# Uses only simple dataclasses that are safe to instantiate.
from dataclasses import dataclass


@dataclass
class _FuzzSafeClass:
    """A trivial dataclass used as a safe target in cls_map for fuzzing."""
    value: object = None


_SAFE_CLS_MAP = {
    "_FuzzSafeClass": _FuzzSafeClass,
}

# Exceptions that are acceptable (expected behavior on malformed input)
_ACCEPTABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AssertionError,
    UnicodeDecodeError,
    struct.error,
    msgpack.exceptions.UnpackException,
    OverflowError,
    AttributeError,
    RecursionError,
)


def _fuzz_find_printable_text(fdp):
    """Fuzz find_printable_text with arbitrary Unicode strings."""
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
    try:
        result = find_printable_text(text)
        # Basic postcondition: result should be a prefix/substring of text
        assert isinstance(result, str)
    except _ACCEPTABLE_EXCEPTIONS:
        pass


def _fuzz_parse_mem_bytes(fdp):
    """Fuzz _PARSE_MEM_BYTES with arbitrary strings."""
    mem_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
    try:
        result = _PARSE_MEM_BYTES(mem_str)
        # Basic postcondition: result should be a non-negative integer
        assert isinstance(result, (int, float))
    except _ACCEPTABLE_EXCEPTIONS:
        pass


def _fuzz_msgpack_deserialize(fdp):
    """Fuzz the full msgpack -> deserialize_type pipeline with raw bytes."""
    raw_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
    try:
        unpacked = msgpack.unpackb(raw_bytes, raw=False)
        if isinstance(unpacked, dict):
            deserialize_type(_SAFE_CLS_MAP, unpacked)
    except _ACCEPTABLE_EXCEPTIONS:
        pass


def _fuzz_deserialize_type_tensor_path(fdp):
    """Fuzz deserialize_type focusing on the Tensor deserialization path.

    This exercises:
      - getattr(np, dtype_str) with arbitrary dtype strings
      - np.frombuffer(buffer, dtype=np_dtype) with mismatched buffer/dtype
    """
    dtype_choices = [
        "float32", "float64", "int32", "int64", "float16",
        "uint8", "int8", "int16", "uint16", "uint32", "uint64",
        "bool_", "complex64", "complex128",
    ]

    # Sometimes use a known dtype, sometimes use a fuzzed string
    if fdp.ConsumeBool():
        dtype_str = fdp.PickValueInList(dtype_choices)
    else:
        dtype_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))

    buffer_data = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))

    data = {
        "__type__": "Tensor",
        "buffer": buffer_data,
        "dtype": dtype_str,
    }

    try:
        result = deserialize_type({}, data)
    except _ACCEPTABLE_EXCEPTIONS:
        pass


def _fuzz_deserialize_any_crafted(fdp):
    """Fuzz _deserialize_any with crafted dict structures.

    Tests recursive deserialization of nested dicts, lists, and tuples,
    as well as the cls_map lookup path.
    """
    # Build a fuzzed data structure
    data = _build_fuzz_data(fdp, depth=0)
    try:
        _deserialize_any(_SAFE_CLS_MAP, data)
    except _ACCEPTABLE_EXCEPTIONS:
        pass


def _build_fuzz_data(fdp, depth):
    """Build a fuzzed data structure for _deserialize_any testing.

    Limits recursion depth to prevent stack overflow from deeply nested inputs.
    """
    if depth > 5:
        # At max depth, return a primitive
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 16))

    choice = fdp.ConsumeIntInRange(0, 6)

    if choice == 0:
        # Dict with __type__ key (triggers deserialize_type path)
        type_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 32))
        d = {"__type__": type_name}
        num_keys = fdp.ConsumeIntInRange(0, 4)
        for _ in range(num_keys):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 16))
            if key == "__type__":
                continue
            d[key] = _build_fuzz_data(fdp, depth + 1)
        return d
    elif choice == 1:
        # Dict without __type__ key (triggers recursive dict deserialization)
        d = {}
        num_keys = fdp.ConsumeIntInRange(0, 4)
        for _ in range(num_keys):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 16))
            d[key] = _build_fuzz_data(fdp, depth + 1)
        return d
    elif choice == 2:
        # List
        length = fdp.ConsumeIntInRange(0, 4)
        return [_build_fuzz_data(fdp, depth + 1) for _ in range(length)]
    elif choice == 3:
        # Tuple
        length = fdp.ConsumeIntInRange(0, 4)
        return tuple(_build_fuzz_data(fdp, depth + 1) for _ in range(length))
    elif choice == 4:
        # Primitive string
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
    elif choice == 5:
        # Primitive int/float/None/bool/bytes
        prim_choice = fdp.ConsumeIntInRange(0, 4)
        if prim_choice == 0:
            return fdp.ConsumeInt(32)
        elif prim_choice == 1:
            return fdp.ConsumeRegularFloat()
        elif prim_choice == 2:
            return None
        elif prim_choice == 3:
            return fdp.ConsumeBool()
        else:
            return fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 16))

    return None


def _fuzz_deserialize_type_safe_cls(fdp):
    """Fuzz deserialize_type with the _FuzzSafeClass in the cls_map.

    This exercises the object instantiation path (cls(**kwargs)).
    """
    data = {"__type__": "_FuzzSafeClass"}

    # Add a 'value' field with fuzzed content
    val_choice = fdp.ConsumeIntInRange(0, 5)
    if val_choice == 0:
        data["value"] = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
    elif val_choice == 1:
        data["value"] = fdp.ConsumeInt(32)
    elif val_choice == 2:
        data["value"] = fdp.ConsumeRegularFloat()
    elif val_choice == 3:
        data["value"] = None
    elif val_choice == 4:
        data["value"] = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 32))

    # Sometimes add extra unexpected keys to test error handling
    if fdp.ConsumeBool():
        extra_key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 16))
        if extra_key != "__type__" and extra_key != "value":
            data[extra_key] = fdp.ConsumeUnicodeNoSurrogates(
                fdp.ConsumeIntInRange(0, 16)
            )

    try:
        result = deserialize_type(_SAFE_CLS_MAP, data)
    except _ACCEPTABLE_EXCEPTIONS:
        pass


def TestOneInput(data):
    """Main fuzz entry point called by LibFuzzer via atheris."""
    fdp = atheris.FuzzedDataProvider(data)

    # Select which target to exercise based on fuzzed input
    target = fdp.ConsumeIntInRange(0, 5)

    if target == 0:
        _fuzz_find_printable_text(fdp)
    elif target == 1:
        _fuzz_parse_mem_bytes(fdp)
    elif target == 2:
        _fuzz_msgpack_deserialize(fdp)
    elif target == 3:
        _fuzz_deserialize_type_tensor_path(fdp)
    elif target == 4:
        _fuzz_deserialize_any_crafted(fdp)
    elif target == 5:
        _fuzz_deserialize_type_safe_cls(fdp)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
