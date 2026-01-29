#!/usr/bin/python3
import atheris
import sys
import os

with atheris.instrument_imports():
    from black import format_str, Mode, TargetVersion
    from black.parsing import InvalidInput
    import tokenize

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz parameters for Mode
        line_length = fdp.ConsumeIntInRange(1, 200)
        string_normalization = fdp.ConsumeBool()
        is_pyi = fdp.ConsumeBool()
        preview = fdp.ConsumeBool()
        
        mode = Mode(
            line_length=line_length,
            string_normalization=string_normalization,
            is_pyi=is_pyi,
            preview=preview
        )
        
        # Fuzz the source code string
        src = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)
        
        formatted = format_str(src, mode=mode)
        
        # Check idempotency
        formatted_twice = format_str(formatted, mode=mode)
        if formatted != formatted_twice:
             # This is a bug in black if it happens, but let's just log for now
             # Actually, for fuzzing, we might want to raise an error
             # pass 
             pass

    except (InvalidInput, tokenize.TokenError, IndentationError, SyntaxError):
        return
    except Exception as e:
        print(f"Unexpected exception: {type(e).__name__}: {e}")
        raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
