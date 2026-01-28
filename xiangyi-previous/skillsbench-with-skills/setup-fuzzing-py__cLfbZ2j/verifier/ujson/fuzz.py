#!/usr/bin/env python3
"""Fuzz driver for ujson library - fast JSON encoder/decoder."""

import sys
import atheris

with atheris.instrument_imports():
    import ujson


def TestOneInput(data):
    """Fuzz target for ujson library."""
    fdp = atheris.FuzzedDataProvider(data)
    
    try:
        # Test ujson.loads() with random JSON strings
        if fdp.ConsumeBool():
            json_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 2000))
            try:
                ujson.loads(json_str)
            except (ujson.JSONDecodeError, ValueError, TypeError):
                pass
        
        # Test ujson.loads() with bytes input
        elif fdp.ConsumeBool():
            json_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1000))
            try:
                ujson.loads(json_bytes)
            except (ujson.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError):
                pass
        
        # Test ujson.dumps() with random Python objects
        elif fdp.ConsumeBool():
            # Create random nested structure
            try:
                obj = {
                    "str": fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 100)),
                    "int": fdp.ConsumeInt(8),
                    "float": fdp.ConsumeFloat(),
                    "bool": fdp.ConsumeBool(),
                    "null": None,
                    "list": [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))],
                }
                ujson.dumps(obj)
            except (ValueError, TypeError, OverflowError):
                pass
        
        # Test ujson.dumps() with special float values
        elif fdp.ConsumeBool():
            special_floats = [float('inf'), float('-inf'), float('nan')]
            idx = fdp.ConsumeIntInRange(0, 2)
            try:
                ujson.dumps({"value": special_floats[idx]}, allow_nan=True)
            except (ValueError, TypeError):
                pass
        
        # Test with deeply nested structures
        elif fdp.ConsumeBool():
            depth = fdp.ConsumeIntInRange(0, 100)
            obj = {"value": "test"}
            for _ in range(depth):
                obj = {"nested": obj}
            try:
                json_str = ujson.dumps(obj)
                ujson.loads(json_str)
            except (ValueError, TypeError, RecursionError, ujson.JSONDecodeError):
                pass
        
        # Test ujson.dumps() with various options
        elif fdp.ConsumeBool():
            obj = {fdp.ConsumeUnicodeNoSurrogates(10): fdp.ConsumeUnicodeNoSurrogates(20)}
            try:
                ujson.dumps(
                    obj,
                    ensure_ascii=fdp.ConsumeBool(),
                    encode_html_chars=fdp.ConsumeBool(),
                    escape_forward_slashes=fdp.ConsumeBool(),
                    sort_keys=fdp.ConsumeBool(),
                )
            except (ValueError, TypeError):
                pass
        
        # Test with incomplete/truncated JSON
        else:
            # Generate partial JSON strings
            partial_json = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 500))
            try:
                ujson.loads(partial_json)
            except (ujson.JSONDecodeError, ValueError, TypeError):
                pass
                
    except Exception:
        # Catch any unexpected exceptions
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
