#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL - LLM inference framework
Focuses on configuration and parameter validation (NOT GPU/model code)
"""
import sys
import os
import atheris

# Add the python directory to the path for minisgl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

# Import after atheris for better instrumentation
with atheris.instrument_imports():
    import msgpack
    from minisgl.core import SamplingParams


def TestOneInput(data):
    """Fuzz MiniSGL configuration and message handling"""
    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: SamplingParams creation with random values
    try:
        temperature = fdp.ConsumeFloat()
        top_k = fdp.ConsumeInt(4)
        top_p = fdp.ConsumeFloat()
        ignore_eos = fdp.ConsumeBool()
        max_tokens = fdp.ConsumeInt(4)

        # Try to create SamplingParams with these values
        params = SamplingParams(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            ignore_eos=ignore_eos,
            max_tokens=max_tokens
        )

        # Test the is_greedy property
        _ = params.is_greedy
    except (ValueError, TypeError, AssertionError, OverflowError):
        # Expected exceptions for invalid parameters
        pass

    # Test 2: msgpack deserialization (message handling)
    if fdp.remaining_bytes() > 10:
        msgpack_data = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            # Try to unpack potentially malformed msgpack data
            obj = msgpack.unpackb(msgpack_data, strict_map_key=False)
        except (msgpack.exceptions.ExtraData,
                msgpack.exceptions.UnpackException,
                msgpack.exceptions.StackError,
                ValueError, TypeError, MemoryError):
            # Expected exceptions for malformed data
            pass

    # Test 3: Validate parameter combinations
    if fdp.remaining_bytes() > 16:
        try:
            # Test edge cases for temperature and top_k/top_p
            temp = fdp.ConsumeFloatInRange(-10.0, 10.0)
            top_k = fdp.ConsumeIntInRange(-100, 1000)
            top_p = fdp.ConsumeFloatInRange(-1.0, 2.0)
            max_tok = fdp.ConsumeIntInRange(-1000, 100000)

            params = SamplingParams(
                temperature=temp,
                top_k=top_k,
                top_p=top_p,
                max_tokens=max_tok
            )
        except (ValueError, TypeError, AssertionError, OverflowError):
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
