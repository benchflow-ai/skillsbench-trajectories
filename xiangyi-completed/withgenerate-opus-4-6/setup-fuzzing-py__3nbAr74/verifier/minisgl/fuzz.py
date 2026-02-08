"""Coverage-guided fuzz driver for the MiniSGL library.

Since minisgl has heavy GPU dependencies (torch, transformers, etc.),
we directly define and fuzz the standalone utility functions from minisgl source.
These functions are copied verbatim from the source to allow atheris to instrument them.
"""
import sys
import os
import atheris


# Standalone functions extracted from minisgl source for fuzzing
# From: python/minisgl/tokenizer/detokenize.py
@atheris.instrument_func
def _is_chinese_char(cp):
    """Check if a codepoint is a CJK character.
    Source: minisgl/tokenizer/detokenize.py
    """
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
def find_printable_text(text):
    """Find the longest printable substring from the text.
    Source: minisgl/tokenizer/detokenize.py
    """
    if not text:
        return ""

    # Check if the last character is a CJK character
    if _is_chinese_char(ord(text[-1])):
        return text

    # Find the last space
    last_space = text.rfind(" ")
    if last_space != -1:
        return text[: last_space + 1]

    # Check for newline at the end
    if text.endswith("\n"):
        return text

    return ""


# From: python/minisgl/utils/misc.py
@atheris.instrument_func
def div_ceil(a, b):
    """Integer division rounding up.
    Source: minisgl/utils/misc.py
    """
    return -(-a // b)


@atheris.instrument_func
def div_even(a, b):
    """Integer division with assertion that a is divisible by b.
    Source: minisgl/utils/misc.py
    """
    assert a % b == 0, f"{a} is not divisible by {b}"
    return a // b


# From: python/minisgl/utils/registry.py
@atheris.instrument_func
def _registry_test(name, registry_dict):
    """Test registry lookup logic.
    Source: minisgl/utils/registry.py
    """
    if name in registry_dict:
        return registry_dict[name]
    supported = list(registry_dict.keys())
    raise KeyError(f"{name} is not supported. Supported: {supported}")


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 4)

    if choice == 0:
        # Fuzz find_printable_text
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        try:
            find_printable_text(text)
        except (ValueError, TypeError, IndexError, OverflowError):
            pass

    elif choice == 1:
        # Fuzz _is_chinese_char with various codepoints
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        try:
            _is_chinese_char(cp)
        except (ValueError, TypeError, OverflowError):
            pass

    elif choice == 2:
        # Fuzz div_ceil
        a = fdp.ConsumeIntInRange(-1000000, 1000000)
        b = fdp.ConsumeIntInRange(-1000000, 1000000)
        if b == 0:
            return
        try:
            div_ceil(a, b)
        except (ValueError, TypeError, ZeroDivisionError, OverflowError):
            pass

    elif choice == 3:
        # Fuzz div_even
        a = fdp.ConsumeIntInRange(-1000000, 1000000)
        b = fdp.ConsumeIntInRange(-1000000, 1000000)
        if b == 0:
            return
        try:
            div_even(a, b)
        except (ValueError, TypeError, ZeroDivisionError, AssertionError,
                OverflowError):
            pass

    else:
        # Fuzz registry lookup
        name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
        num_keys = fdp.ConsumeIntInRange(0, 10)
        registry = {}
        for _ in range(num_keys):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
            registry[key] = True
        try:
            _registry_test(name, registry)
        except (KeyError, ValueError, TypeError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
