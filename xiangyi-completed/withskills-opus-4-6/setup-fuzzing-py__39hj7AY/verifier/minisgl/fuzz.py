#!/usr/bin/python3
"""Coverage-guided fuzz driver for minisgl.

Targets:
  1. find_printable_text()  - Unicode-aware word boundary detection
  2. _PARSE_MEM_BYTES()     - Memory size string parsing
  3. deserialize_type()     - Object deserialization from dicts

These targets are chosen because they don't require GPU or heavy
external dependencies (torch tensors are CPU-only, msgpack is standard).
"""
import sys
sys.path.insert(0, "/app/minisgl/python")

import atheris
import numpy as np

# Only instrument the specific minisgl modules we're fuzzing
with atheris.instrument_imports(include=[
    "minisgl.tokenizer.detokenize",
    "minisgl.env",
    "minisgl.message.utils",
]):
    from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
    from minisgl.env import _PARSE_MEM_BYTES
    from minisgl.message.utils import deserialize_type, _deserialize_any

# Set up a simple cls_map for deserialize_type fuzzing
from dataclasses import dataclass

@dataclass
class DummyMsg:
    x: int = 0
    y: str = ""
    z: float = 0.0

_cls_map = {"DummyMsg": DummyMsg}


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    if fdp.remaining_bytes() < 2:
        return
    target = fdp.ConsumeIntInRange(0, 2)

    if target == 0:
        # Target 1: find_printable_text - pure string processing
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            result = find_printable_text(text)
            assert isinstance(result, str)
        except (ValueError, TypeError, IndexError, OverflowError):
            pass

    elif target == 1:
        # Target 2: _PARSE_MEM_BYTES - memory size string parser
        mem_str = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        try:
            result = _PARSE_MEM_BYTES(mem_str)
        except (ValueError, KeyError, IndexError, TypeError, OverflowError):
            pass

    elif target == 2:
        # Target 3: deserialize_type - dict-based deserialization
        # Build a fuzzed dict with __type__ field
        type_name = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 64)
        )
        fuzzed_dict = {"__type__": type_name}

        # Add some fuzzed fields
        num_fields = fdp.ConsumeIntInRange(0, 5)
        for i in range(num_fields):
            key = fdp.ConsumeUnicodeNoSurrogates(
                fdp.ConsumeIntInRange(0, 32)
            )
            # Alternate between string, int, and bytes values
            vtype = fdp.ConsumeIntInRange(0, 2)
            if vtype == 0:
                val = fdp.ConsumeUnicodeNoSurrogates(
                    fdp.ConsumeIntInRange(0, 64)
                )
            elif vtype == 1:
                val = fdp.ConsumeInt(4)
            else:
                val = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 64))
            fuzzed_dict[key] = val

        # Also test Tensor deserialization path
        if type_name == "" and fdp.remaining_bytes() > 0:
            fuzzed_dict["__type__"] = "Tensor"
            fuzzed_dict["buffer"] = fdp.ConsumeBytes(fdp.remaining_bytes())
            dtype_choices = ["float32", "float64", "int32", "int64",
                             "float16", "int16", "int8", "uint8"]
            fuzzed_dict["dtype"] = "torch." + fdp.PickValueInList(dtype_choices)

        try:
            deserialize_type(_cls_map, fuzzed_dict)
        except (KeyError, ValueError, TypeError, AttributeError,
                AssertionError, IndexError, OverflowError,
                RuntimeError, BufferError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
