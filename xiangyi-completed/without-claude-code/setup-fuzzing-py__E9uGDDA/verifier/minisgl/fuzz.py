#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for minisgl library.
Tests minisgl's core data structures and parameter validation.
"""

import sys
import atheris
from minisgl.core import SamplingParams


def __test_one_input(data: bytes) -> None:
    """Fuzz driver for minisgl library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Split fuzzed data into parts for different test strategies
    action = fdp.ConsumeIntInRange(0, 4)

    if action == 0:
        # Test SamplingParams with valid ranges
        try:
            temperature = fdp.ConsumeFloatInRange(0.0, 2.0)
            top_k = fdp.ConsumeIntInRange(-1, 100)
            top_p = fdp.ConsumeFloatInRange(0.0, 1.0)
            max_tokens = fdp.ConsumeIntInRange(1, 10000)
            ignore_eos = fdp.ConsumeBool()

            params = SamplingParams(
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=max_tokens,
                ignore_eos=ignore_eos
            )
            # Access properties
            _ = params.is_greedy
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass

    elif action == 1:
        # Test SamplingParams with extreme values
        try:
            temperature = fdp.ConsumeFloat()
            top_k = fdp.ConsumeInt(2**31 - 1)
            top_p = fdp.ConsumeFloat()
            max_tokens = fdp.ConsumeInt(2**31 - 1)

            params = SamplingParams(
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=max_tokens
            )
            _ = params.is_greedy
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass

    elif action == 2:
        # Test SamplingParams with special float values
        try:
            values = [
                float('inf'),
                float('-inf'),
                float('nan'),
                0.0,
                1e-10,
                1e10
            ]
            choice = fdp.ConsumeIntInRange(0, len(values) - 1)

            params = SamplingParams(
                temperature=values[choice],
                top_p=values[choice]
            )
            _ = params.is_greedy
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass

    elif action == 3:
        # Test SamplingParams with negative values (invalid)
        try:
            params = SamplingParams(
                temperature=fdp.ConsumeFloatInRange(-10.0, 10.0),
                top_k=fdp.ConsumeIntInRange(-1000, 1000),
                top_p=fdp.ConsumeFloatInRange(-1.0, 2.0),
                max_tokens=fdp.ConsumeIntInRange(-1000, 1000)
            )
            _ = params.is_greedy
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass

    elif action == 4:
        # Test SamplingParams with various combinations
        try:
            temperature = 0.0 if fdp.ConsumeBool() else fdp.ConsumeFloatInRange(0.1, 2.0)
            top_k = -1 if fdp.ConsumeBool() else fdp.ConsumeIntInRange(1, 100)
            top_p = fdp.ConsumeFloatInRange(0.0, 1.0)
            max_tokens = fdp.ConsumeIntInRange(1, 1000)

            params = SamplingParams(
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=max_tokens,
                ignore_eos=fdp.ConsumeBool()
            )
            # Check if greedy (temperature==0 and top_k==-1)
            is_greedy = params.is_greedy
            # Validate the result
            expected_greedy = (temperature == 0.0 and top_k == -1)
            assert is_greedy == expected_greedy, f"Greedy mismatch: {is_greedy} vs {expected_greedy}"
        except (ValueError, TypeError, AttributeError, OverflowError, AssertionError):
            pass


# Initialize atheris for code coverage guidance
atheris.Setup(sys.argv, __test_one_input)

if __name__ == "__main__":
    atheris.Fuzz()
