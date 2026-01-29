#!/usr/bin/env python3
"""Coverage-guided fuzzing for MiniSGL library."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for MiniSGL library."""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Import minisgl components inside to ensure instrumentation
    try:
        from minisgl.message.utils import serialize_type, deserialize_type
    except ImportError:
        # Fallback if message module not available
        return

    # Test 1: Deserialize arbitrary dictionaries
    try:
        # Create a fuzzed dictionary with type information
        type_name = fdp.ConsumeUnicodeNoSurrogates(50)
        field_name = fdp.ConsumeUnicodeNoSurrogates(30)
        field_value = fdp.ConsumeUnicodeNoSurrogates(100)

        test_dict = {
            "__type__": type_name,
            field_name: field_value,
        }

        # Try to deserialize with empty class map
        deserialize_type({}, test_dict)
    except (ValueError, KeyError, TypeError, AttributeError, AssertionError):
        pass

    # Test 2: Deserialize with tensor-like bytes
    try:
        type_name = fdp.ConsumeUnicodeNoSurrogates(30)
        dtype_choices = ["float32", "float16", "int32", "int64", "uint8", "invalid"]
        dtype = dtype_choices[fdp.ConsumeIntInRange(0, len(dtype_choices) - 1)]
        tensor_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000))

        test_dict = {
            "__type__": "torch.Tensor",
            "dtype": dtype,
            "data": tensor_bytes,
        }
        deserialize_type({}, test_dict)
    except (ValueError, KeyError, TypeError, AttributeError, AssertionError,
            RuntimeError, ImportError):
        pass

    # Test 3: Serialize Python objects
    try:
        # Create nested structure
        nested = {
            "key1": fdp.ConsumeUnicodeNoSurrogates(100),
            "key2": fdp.ConsumeIntInRange(-1000000, 1000000),
            "key3": [fdp.ConsumeUnicodeNoSurrogates(50) for _ in range(3)],
        }
        serialize_type(nested)
    except (ValueError, TypeError, AttributeError, AssertionError, RuntimeError):
        pass

    # Test 4: Test sampling params if available
    try:
        from minisgl.core import SamplingParams

        temp = fdp.ConsumeFloat()
        top_k = fdp.ConsumeIntInRange(-1, 1000)
        top_p = fdp.ConsumeFloat()
        max_tokens = fdp.ConsumeIntInRange(-100, 10000)

        params = SamplingParams(
            temperature=temp,
            top_k=top_k,
            top_p=top_p,
            max_new_tokens=max_tokens,
        )
    except (ValueError, TypeError, AttributeError, AssertionError, ImportError):
        pass

    # Test 5: Test model config parsing if available
    try:
        from minisgl.models.config import ModelConfig

        # Create a mock config-like object
        class MockConfig:
            pass

        config = MockConfig()
        config.hidden_size = fdp.ConsumeIntInRange(0, 10000)
        config.num_attention_heads = fdp.ConsumeIntInRange(0, 100)
        config.num_hidden_layers = fdp.ConsumeIntInRange(0, 100)
        config.vocab_size = fdp.ConsumeIntInRange(0, 100000)
        config.intermediate_size = fdp.ConsumeIntInRange(0, 50000)
        config.num_key_value_heads = fdp.ConsumeIntInRange(0, 100)
        config.rope_theta = fdp.ConsumeFloat()
        config.max_position_embeddings = fdp.ConsumeIntInRange(0, 100000)

        ModelConfig.from_hf(config)
    except (ValueError, TypeError, AttributeError, ZeroDivisionError,
            AssertionError, ImportError):
        pass


def main():
    # Instrument imports
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
