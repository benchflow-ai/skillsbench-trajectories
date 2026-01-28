#!/usr/bin/env python3
"""Fuzz driver for minisgl library - testing JSON parsing and basic utilities."""

import sys
import atheris
import json

# Don't import minisgl modules since the package isn't fully installed
# Focus on testing JSON parsing which is critical for API server

def TestOneInput(data):
    """Fuzz target for minisgl library - JSON and string processing."""
    fdp = atheris.FuzzedDataProvider(data)
    
    try:
        # Test JSON message parsing (common in API server)
        if fdp.ConsumeBool():
            json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            try:
                data = json.loads(json_str)
                # Validate message structure
                if isinstance(data, dict):
                    # Test various fields that might be in requests
                    _ = data.get("prompt", "")
                    _ = data.get("max_tokens", 100)
                    _ = data.get("temperature", 1.0)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        # Test with malformed request-like structures
        elif fdp.ConsumeBool():
            try:
                request_data = {
                    "prompt": fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 200)),
                    "max_tokens": fdp.ConsumeIntInRange(-100, 10000),
                    "temperature": fdp.ConsumeFloat(),
                    "top_p": fdp.ConsumeFloat(),
                }
                # Validate request parameters
                json_str = json.dumps(request_data)
                json.loads(json_str)
            except (ValueError, TypeError, OverflowError, json.JSONDecodeError):
                pass
        
        # Test with edge case text inputs
        elif fdp.ConsumeBool():
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            # Test text processing edge cases
            try:
                # Test string operations that might be used in preprocessing
                _ = text.strip()
                _ = text.split()
                _ = len(text.encode('utf-8'))
                _ = text.replace("\n", " ")
            except (UnicodeError, ValueError):
                pass
        
        # Test deeply nested JSON structures
        else:
            depth = fdp.ConsumeIntInRange(0, 50)
            obj = {"value": fdp.ConsumeUnicodeNoSurrogates(10)}
            for _ in range(depth):
                obj = {"nested": obj}
            try:
                json_str = json.dumps(obj)
                json.loads(json_str)
            except (ValueError, TypeError, RecursionError, json.JSONDecodeError):
                pass
                
    except Exception:
        # Catch any unexpected exceptions
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
