import atheris
import sys

# For minisgl, many modules require GPU (torch/CUDA) dependencies that are
# not available in our fuzzing environment. We directly define the standalone
# functions from the library source for fuzzing, and instrument them manually.

# Inline the pure-Python functions from the library source to enable coverage tracking
@atheris.instrument_func
def _PARSE_MEM_BYTES(mem: str) -> int:
    """From minisgl/env.py - parses memory size strings like '1GB', '512MB'."""
    mem = mem.strip().upper()
    if not mem[-1].isalpha():
        return int(mem)
    if mem.endswith("B"):
        mem = mem[:-1]
    UNIT_MAP = {"K": 1024, "M": 1024**2, "G": 1024**3}
    return int(float(mem[:-1]) * UNIT_MAP[mem[-1]])

@atheris.instrument_func
def _is_chinese_char(cp: int):
    """From minisgl/tokenizer/detokenize.py - checks CJK character codepoints."""
    if (
        (cp >= 0x4E00 and cp <= 0x9FFF)
        or (cp >= 0x3400 and cp <= 0x4DBF)
        or (cp >= 0x20000 and cp <= 0x2A6DF)
        or (cp >= 0x2A700 and cp <= 0x2B73F)
        or (cp >= 0x2B740 and cp <= 0x2B81F)
        or (cp >= 0x2B820 and cp <= 0x2CEAF)
        or (cp >= 0xF900 and cp <= 0xFAFF)
        or (cp >= 0x2F800 and cp <= 0x2FA1F)
    ):
        return True
    return False

@atheris.instrument_func
def find_printable_text(text: str):
    """From minisgl/tokenizer/detokenize.py - returns longest printable substring."""
    if text.endswith("\n"):
        return text
    elif len(text) > 0 and _is_chinese_char(ord(text[-1])):
        return text
    elif len(text) > 1 and _is_chinese_char(ord(text[-2])):
        return text[:-1]
    else:
        return text[: text.rfind(" ") + 1]


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not text:
        return

    # Fuzz _PARSE_MEM_BYTES with string input
    try:
        _PARSE_MEM_BYTES(text)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        pass

    # Fuzz find_printable_text
    try:
        find_printable_text(text)
    except (ValueError, TypeError, IndexError):
        pass

    # Fuzz _is_chinese_char with various codepoints
    try:
        for ch in text[:10]:
            _is_chinese_char(ord(ch))
    except (ValueError, TypeError, OverflowError):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
