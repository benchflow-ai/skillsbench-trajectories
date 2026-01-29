#!/usr/bin/env python3
"""Fuzz driver for minisgl library - focusing on core data structures.

Note: This library has heavy dependencies (torch, transformers, CUDA).
We focus on fuzzing the core dataclasses that can be tested without
loading ML models.
"""

import sys
import os

# Add the python directory to path so we can import minisgl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

import atheris


def TestOneInput(data: bytes) -> None:
    """Main fuzz target function for minisgl core structures."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: SamplingParams with various values
    try:
        from minisgl.core import SamplingParams

        temperature = fdp.ConsumeFloat()
        top_k = fdp.ConsumeInt(4)
        top_p = fdp.ConsumeFloat()
        max_tokens = fdp.ConsumeInt(4)
        ignore_eos = fdp.ConsumeBool()

        params = SamplingParams(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            max_tokens=max_tokens,
            ignore_eos=ignore_eos,
        )

        # Test derived properties
        _ = params.is_greedy

    except (ValueError, TypeError, OverflowError, ImportError, AssertionError):
        pass

    # Test 2: SamplingParams edge cases with bounded values
    try:
        from minisgl.core import SamplingParams

        # Test with extreme values
        params = SamplingParams(
            temperature=fdp.ConsumeFloatInRange(-1e10, 1e10),
            top_k=fdp.ConsumeIntInRange(-1000000, 1000000),
            top_p=fdp.ConsumeFloatInRange(-1e10, 1e10),
            max_tokens=fdp.ConsumeIntInRange(-1000000, 1000000),
        )
        _ = params.is_greedy

    except (ValueError, TypeError, OverflowError, ImportError, AssertionError):
        pass

    # Test 3: Test message structures
    try:
        from minisgl.core import SamplingParams
        from minisgl.message.tokenizer import TokenizeMsg, DetokenizeMsg

        # Test TokenizeMsg with string text
        text = fdp.ConsumeUnicodeNoSurrogates(
            fdp.ConsumeIntInRange(0, 500)
        )
        uid = fdp.ConsumeInt(4)
        params = SamplingParams()
        msg = TokenizeMsg(text=text, uid=uid, sampling_params=params)

    except (ValueError, TypeError, ImportError, AttributeError):
        pass

    # Test 4: Test DetokenizeMsg
    try:
        from minisgl.message.tokenizer import DetokenizeMsg

        uid = fdp.ConsumeInt(4)
        next_token = fdp.ConsumeInt(4)
        finished = fdp.ConsumeBool()
        msg = DetokenizeMsg(uid=uid, next_token=next_token, finished=finished)

    except (ValueError, TypeError, ImportError, AttributeError):
        pass

    # Test 5: SamplingParams with normal ranges (more realistic)
    try:
        from minisgl.core import SamplingParams

        params = SamplingParams(
            temperature=fdp.ConsumeFloatInRange(0.0, 2.0),
            top_k=fdp.ConsumeIntInRange(-1, 100),
            top_p=fdp.ConsumeFloatInRange(0.0, 1.0),
            max_tokens=fdp.ConsumeIntInRange(1, 8192),
            ignore_eos=fdp.ConsumeBool(),
        )
        _ = params.is_greedy

    except (ValueError, TypeError, OverflowError, ImportError, AssertionError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
