#!/usr/bin/python3
import atheris
import sys
import os

with atheris.instrument_imports():
    from minisgl.tokenizer.detokenize import _is_chinese_char, find_printable_text

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    
    try:
        # Fuzz _is_chinese_char
        cp = fdp.ConsumeIntInRange(0, 0x110000)
        _is_chinese_char(cp)
        
        # Fuzz find_printable_text
        s = fdp.ConsumeUnicodeNoSurrogates(1000)
        find_printable_text(s)

    except (ValueError, OverflowError):
        return
    except Exception as e:
        print(f"Unexpected exception: {type(e).__name__}: {e}")
        raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
