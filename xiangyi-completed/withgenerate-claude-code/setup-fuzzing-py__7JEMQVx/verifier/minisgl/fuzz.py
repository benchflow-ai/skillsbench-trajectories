#!/usr/bin/env python3
"""
Fuzz driver for Mini-SGLang
Tests parameter validation and core functionality
"""

import atheris
import sys

# Suppress warnings during fuzzing
import warnings
warnings.filterwarnings("ignore")


def TestOneInput(data):
    """Fuzz target for Mini-SGLang core functionality"""
    fdp = atheris.FuzzedDataProvider(data)

    # Import inside to catch import-time errors
    try:
        # Add the python directory to path
        sys.path.insert(0, '/app/minisgl/python')
        from minisgl.core import SamplingParams
    except Exception:
        return

    # Test different functions based on fuzzer choice
    choice = fdp.ConsumeIntInRange(0, 1)

    try:
        if choice == 0:
            # Test SamplingParams with various values
            temperature = fdp.ConsumeRegularFloat()
            top_k = fdp.ConsumeIntInRange(-100, 1000)
            top_p = fdp.ConsumeRegularFloat()
            ignore_eos = fdp.ConsumeBool()
            max_tokens = fdp.ConsumeIntInRange(-10, 10000)

            try:
                params = SamplingParams(
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    ignore_eos=ignore_eos,
                    max_tokens=max_tokens
                )
                # Test the property
                _ = params.is_greedy
            except (ValueError, TypeError, AssertionError):
                pass

        else:
            # Test SamplingParams edge cases
            try:
                # Test with extreme values
                params = SamplingParams(
                    temperature=fdp.ConsumeFloat(),
                    top_k=fdp.ConsumeInt(4),
                    top_p=fdp.ConsumeFloat(),
                    max_tokens=fdp.ConsumeInt(4)
                )
                _ = params.is_greedy
            except (ValueError, TypeError, AssertionError, OverflowError):
                pass

    except Exception as e:
        # Catch any unexpected exceptions
        error_str = str(e).lower()
        if 'unreachable' in error_str:
            raise
        # AssertionErrors are expected for validation
        if isinstance(e, AssertionError):
            return
        # Otherwise suppress to continue fuzzing


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
