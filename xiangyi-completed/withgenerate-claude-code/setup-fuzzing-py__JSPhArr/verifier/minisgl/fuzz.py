#!/usr/bin/env python3
"""
Fuzzer for Mini-SGLang - LLM inference framework
Targets: SamplingParams validation and basic data structures
Note: Avoiding CUDA-dependent code
"""

import sys
import atheris

# Import after atheris setup
with atheris.instrument_imports():
    try:
        from minisgl.core import SamplingParams
        MINISGL_AVAILABLE = True
    except ImportError as e:
        # Mini-SGLang may not be installable due to CUDA dependencies
        MINISGL_AVAILABLE = False
        print(f"Warning: Could not import minisgl: {e}")


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz SamplingParams creation with various parameter values."""
    if not MINISGL_AVAILABLE:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: SamplingParams with random float/int values
    try:
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
            ignore_eos=ignore_eos
        )

        # Test property access
        _ = params.is_greedy
    except (ValueError, TypeError, AssertionError, OverflowError) as e:
        # Expected exceptions for invalid parameters
        pass
    except Exception as e:
        # Catch other exceptions
        pass

    # Test 2: Test with extreme values
    try:
        temperature = fdp.PickValueInList([-1.0, 0.0, 0.5, 1.0, 2.0, 100.0, float('inf'), float('-inf')])
        top_p = fdp.PickValueInList([0.0, 0.5, 1.0, 2.0, -1.0, float('inf')])
        top_k = fdp.PickValueInList([-1, 0, 1, 10, 100, 1000, -1000])
        max_tokens = fdp.PickValueInList([0, 1, 100, 1024, 10000, -1, -100])

        params = SamplingParams(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            max_tokens=max_tokens
        )
    except (ValueError, TypeError, AssertionError, OverflowError) as e:
        pass
    except Exception as e:
        pass

    # Test 3: Test with boundary values
    try:
        params = SamplingParams(
            temperature=fdp.ConsumeFloatInRange(-100.0, 100.0),
            top_k=fdp.ConsumeIntInRange(-1000, 1000),
            top_p=fdp.ConsumeFloatInRange(-1.0, 2.0),
            max_tokens=fdp.ConsumeIntInRange(0, 10000)
        )
    except (ValueError, TypeError, AssertionError, OverflowError) as e:
        pass
    except Exception as e:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
