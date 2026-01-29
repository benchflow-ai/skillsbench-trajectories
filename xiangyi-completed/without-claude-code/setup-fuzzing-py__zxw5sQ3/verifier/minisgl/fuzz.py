#!/usr/bin/env python3
"""
Atheris-based fuzzer for MiniSGL library
Targets: sampling parameters, configuration parsing, and API request handling
"""

import sys
import atheris
import json

# Suppress output for cleaner fuzzing
import warnings
warnings.filterwarnings("ignore")

with atheris.instrument_imports():
    from minisgl.core import SamplingParams


def TestOneInput(data):
    """Fuzz entry point called by Atheris"""
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz SamplingParams initialization
            temperature = fdp.ConsumeFloat()
            top_k = fdp.ConsumeInt(4)
            top_p = fdp.ConsumeFloat()
            max_tokens = fdp.ConsumeInt(4)
            ignore_eos = fdp.ConsumeBool()

            SamplingParams(
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=max_tokens,
                ignore_eos=ignore_eos
            )

        elif choice == 1:
            # Fuzz SamplingParams with boundary values
            params = {
                'temperature': fdp.PickValueInList([0.0, -1.0, 1.0, 2.0, 100.0, float('inf'), float('-inf')]),
                'top_k': fdp.PickValueInList([-1, 0, 1, 50, 1000, 2**31]),
                'top_p': fdp.PickValueInList([0.0, 0.5, 1.0, -1.0, 2.0]),
                'max_tokens': fdp.PickValueInList([0, 1, 1000, 2**20, -1]),
            }
            SamplingParams(**params)

        elif choice == 2:
            # Fuzz JSON API request format (simulated)
            request_data = {
                'prompt': fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500)),
                'max_tokens': fdp.ConsumeInt(4),
                'temperature': fdp.ConsumeFloat(),
                'top_p': fdp.ConsumeFloat(),
                'top_k': fdp.ConsumeInt(4),
                'stop': fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 50)),
                'stream': fdp.ConsumeBool(),
            }
            # Just validate JSON serialization
            json.dumps(request_data)

        elif choice == 3:
            # Fuzz SamplingParams with random keyword arguments
            kwargs = {}
            num_args = fdp.ConsumeIntInRange(1, 5)
            for _ in range(num_args):
                key = fdp.PickValueInList(['temperature', 'top_k', 'top_p', 'max_tokens', 'ignore_eos'])
                if 'temperature' in key or 'top_p' in key:
                    kwargs[key] = fdp.ConsumeFloat()
                elif 'ignore_eos' in key:
                    kwargs[key] = fdp.ConsumeBool()
                else:
                    kwargs[key] = fdp.ConsumeInt(4)
            SamplingParams(**kwargs)

    except (ValueError, TypeError, AssertionError, KeyError,
            json.JSONDecodeError, OverflowError):
        # Expected exceptions during fuzzing
        pass
    except Exception as e:
        # Catch unexpected exceptions
        error_msg = str(e).lower()
        if any(x in error_msg for x in ["cuda", "gpu", "torch", "model", "device"]):
            # Skip GPU/model-related errors during fuzzing
            pass
        else:
            # Re-raise to find bugs
            raise


def main():
    """Initialize and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
