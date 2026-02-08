"""Coverage-guided fuzzer for Mini-SGLang utility functions using atheris + LibFuzzer."""

import sys
import os

# Add the python source directory to the path so minisgl is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

import atheris


def TestOneInput(data: bytes):
    """Fuzz target for minisgl's utility and parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
    from minisgl.message.utils import _deserialize_any, deserialize_type

    # Fuzz find_printable_text
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
    try:
        find_printable_text(text)
    except Exception:
        pass

    # Fuzz _is_chinese_char with various code points
    cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
    try:
        _is_chinese_char(cp)
    except Exception:
        pass

    # Fuzz _deserialize_any with primitive types
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        val = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
    elif choice == 1:
        val = fdp.ConsumeInt(8)
    elif choice == 2:
        val = fdp.ConsumeFloat()
    elif choice == 3:
        val = None
    else:
        val = fdp.ConsumeBool()

    try:
        _deserialize_any({}, val)
    except Exception:
        pass

    # Fuzz _deserialize_any with list input
    try:
        items = []
        for _ in range(fdp.ConsumeIntInRange(0, 10)):
            items.append(fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32)))
        _deserialize_any({}, items)
    except Exception:
        pass

    # Fuzz _deserialize_any with nested dict (no __type__ key)
    try:
        d = {}
        for _ in range(fdp.ConsumeIntInRange(0, 5)):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
            val = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
            d[key] = val
        _deserialize_any({}, d)
    except Exception:
        pass

    # Fuzz SamplingParams
    from minisgl.core import SamplingParams
    try:
        SamplingParams(
            temperature=fdp.ConsumeFloat(),
            top_k=fdp.ConsumeInt(4),
            top_p=fdp.ConsumeFloat(),
            max_tokens=fdp.ConsumeInt(4),
        )
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
