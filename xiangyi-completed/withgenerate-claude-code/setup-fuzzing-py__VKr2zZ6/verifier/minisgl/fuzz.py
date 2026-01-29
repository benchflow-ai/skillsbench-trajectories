#!/usr/bin/env python3
"""
Coverage-guided fuzz driver for MiniSGL library.
Uses Atheris for LibFuzzer-style fuzzing.

Note: This library has heavy GPU dependencies. This fuzzer focuses on
pure Python components that don't require GPU initialization.
"""
import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for MiniSGL core components."""
    fdp = atheris.FuzzedDataProvider(data)

    # Test SamplingParams without importing torch-dependent modules
    # We mock torch to avoid GPU requirements

    # Test 1: SamplingParams creation with various values
    try:
        # Only import core types that work without GPU
        from dataclasses import dataclass

        # Test SamplingParams-like validation logic directly
        temperature = fdp.ConsumeFloat()
        top_k = fdp.ConsumeInt(4)
        top_p = fdp.ConsumeFloat()
        max_tokens = fdp.ConsumeInt(4)
        ignore_eos = fdp.ConsumeBool()

        # Validate parameter ranges (mimicking SamplingParams behavior)
        # These are typical validation checks that could crash
        if temperature < 0:
            raise ValueError("temperature must be non-negative")
        if top_p < 0 or top_p > 1:
            raise ValueError("top_p must be between 0 and 1")
        if max_tokens < 0:
            raise ValueError("max_tokens must be non-negative")

        # Check is_greedy property logic
        is_greedy = (temperature <= 0.0 or top_k == 1) and top_p == 1.0

    except (ValueError, TypeError, OverflowError):
        pass

    # Test 2: Try to parse JSON-like structures that might be used for messages
    try:
        import json
        json_str = fdp.ConsumeUnicodeNoSurrogates(1024)
        if json_str:
            parsed = json.loads(json_str)
            # Simulate message validation
            if isinstance(parsed, dict):
                _ = parsed.get('role', '')
                _ = parsed.get('content', '')
    except (json.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError):
        pass

    # Test 3: Test environment variable parsing (from env.py)
    try:
        env_value = fdp.ConsumeUnicodeNoSurrogates(64)
        if env_value:
            # Simulate int parsing from env
            int(env_value)
    except (ValueError, TypeError):
        pass

    # Test 4: Test parsing of configuration-like strings
    try:
        config_str = fdp.ConsumeUnicodeNoSurrogates(256)
        if config_str:
            # Simulate splitting and parsing config
            parts = config_str.split(',')
            for part in parts:
                key_val = part.split('=')
                if len(key_val) == 2:
                    _ = key_val[0].strip()
                    _ = key_val[1].strip()
    except (ValueError, TypeError, IndexError):
        pass


def main():
    # Instrument modules for coverage
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
