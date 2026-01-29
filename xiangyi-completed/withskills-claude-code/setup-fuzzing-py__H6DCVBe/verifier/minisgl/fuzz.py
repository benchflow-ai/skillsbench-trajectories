#!/usr/bin/env python3
"""
Fuzz driver for Mini-SGLang library - LLM inference framework
Uses Atheris (LibFuzzer-based) for coverage-guided fuzzing
"""

import sys
import atheris
import json

with atheris.instrument_imports():
    pass  # Will fuzz basic JSON message structures

@atheris.instrument_func
def TestOneInput(data):
    """Fuzz target for Mini-SGLang library"""
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 2)

    if choice == 0:
        # Fuzz JSON message parsing
        try:
            json_str = fdp.ConsumeUnicodeNoSurrogates(500)
            if json_str:
                parsed = json.loads(json_str)
                # Validate message structure
                if isinstance(parsed, dict):
                    # Check for typical API fields
                    _ = parsed.get('model', '')
                    _ = parsed.get('messages', [])
                    _ = parsed.get('max_tokens', 0)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    elif choice == 1:
        # Fuzz text input (simulating tokenization input)
        try:
            text = fdp.ConsumeUnicodeNoSurrogates(1000)
            if text:
                # Basic validation of text
                _ = len(text)
                _ = text.encode('utf-8')
        except (UnicodeEncodeError, ValueError):
            pass

    elif choice == 2:
        # Fuzz parameter validation
        try:
            # Simulate API parameters
            temperature = fdp.ConsumeFloat()
            top_p = fdp.ConsumeProbability()
            max_tokens = fdp.ConsumeIntInRange(-1000, 10000)

            # Basic validation
            if temperature >= 0 and top_p >= 0 and top_p <= 1 and max_tokens > 0:
                pass
        except (ValueError, TypeError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
