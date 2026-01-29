#!/usr/bin/env python3
"""
LibFuzzer-based fuzz driver for MiniSGL library.
Uses atheris for coverage-guided fuzzing.
Focuses on message deserialization and core data structures (avoids GPU/model operations).
"""
import sys
import os

# Add the python package path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

# Pre-import heavy modules before atheris to avoid instrumentation timeout
import numpy as np
import torch
from dataclasses import dataclass

# Define SamplingParams locally to avoid full package import issues
@dataclass
class SamplingParams:
    temperature: float = 0.0
    top_k: int = -1
    top_p: float = 1.0
    ignore_eos: bool = False
    max_tokens: int = 1024

    @property
    def is_greedy(self):
        return (self.temperature <= 0.0 or self.top_k == 1) and self.top_p == 1.0

# Import message utils
from minisgl.message.utils import deserialize_type, serialize_type, _deserialize_any

import atheris


@atheris.instrument_func
def TestOneInput(data: bytes):
    """Fuzz target for MiniSGL library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz deserialize_type() with various data structures
            type_name = fdp.ConsumeUnicodeNoSurrogates(32)

            fuzz_data = {
                "__type__": type_name,
            }

            # Add random fields
            num_fields = fdp.ConsumeIntInRange(0, 5)
            for i in range(num_fields):
                key = fdp.ConsumeUnicodeNoSurrogates(8)
                value_type = fdp.ConsumeIntInRange(0, 4)
                if value_type == 0:
                    fuzz_data[key] = fdp.ConsumeInt(8)
                elif value_type == 1:
                    fuzz_data[key] = fdp.ConsumeFloat()
                elif value_type == 2:
                    fuzz_data[key] = fdp.ConsumeUnicodeNoSurrogates(32)
                elif value_type == 3:
                    fuzz_data[key] = fdp.ConsumeBool()
                elif value_type == 4:
                    fuzz_data[key] = None

            cls_map = {"SamplingParams": SamplingParams}
            deserialize_type(cls_map, fuzz_data)

        elif choice == 1:
            # Fuzz SamplingParams with boundary values
            max_tokens = fdp.ConsumeInt(4)
            temperature = fdp.ConsumeFloat()
            top_k = fdp.ConsumeInt(4)
            top_p = fdp.ConsumeFloat()
            ignore_eos = fdp.ConsumeBool()

            params = SamplingParams(
                max_tokens=max_tokens,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                ignore_eos=ignore_eos,
            )
            _ = params.is_greedy

        elif choice == 2:
            # Fuzz Tensor deserialization with malformed buffer
            dtype_choices = ["float32", "float64", "int32", "int64", "int16", "int8"]
            dtype_str = fdp.PickValueInList(dtype_choices)
            buffer = fdp.ConsumeBytes(64)

            fuzz_data = {
                "__type__": "Tensor",
                "buffer": buffer,
                "dtype": f"torch.{dtype_str}",
            }

            cls_map = {"SamplingParams": SamplingParams}
            deserialize_type(cls_map, fuzz_data)

    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
