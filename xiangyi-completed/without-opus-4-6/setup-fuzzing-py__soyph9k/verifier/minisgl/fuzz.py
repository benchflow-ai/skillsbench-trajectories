"""Coverage-guided fuzz driver for the Mini-SGLang library.

Focuses on serialization/deserialization and text processing utilities
that don't require GPU or heavy ML dependencies.
"""

import sys
import os

# Add the minisgl source to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

import atheris


def TestOneInput(data: bytes):
    """Fuzz target for minisgl serialization and text processing."""
    fdp = atheris.FuzzedDataProvider(data)

    from minisgl.message.utils import (
        _deserialize_any,
        _serialize_any,
        deserialize_type,
    )
    from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char

    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            # Fuzz find_printable_text() with arbitrary strings
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
            find_printable_text(text)

        elif choice == 1:
            # Fuzz _is_chinese_char() with various code points
            cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
            _is_chinese_char(cp)

        elif choice == 2:
            # Fuzz _deserialize_any with constructed dicts
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
            num = fdp.ConsumeFloat()
            # Test with various primitive types
            _deserialize_any({}, text)
            _deserialize_any({}, num)
            _deserialize_any({}, None)
            _deserialize_any({}, fdp.ConsumeIntInRange(-1000000, 1000000))
            # Test with nested structures
            nested = {
                "key": text,
                "num": num,
                "list": [text, num, None],
            }
            _deserialize_any({}, nested)

        elif choice == 3:
            # Fuzz _serialize_any with various inputs
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
            _serialize_any(text)
            _serialize_any(fdp.ConsumeIntInRange(-1000000, 1000000))
            _serialize_any(fdp.ConsumeFloat())
            _serialize_any(None)
            _serialize_any([text, fdp.ConsumeFloat(), None])
            _serialize_any({"key": text, "val": fdp.ConsumeIntInRange(0, 100)})

        elif choice == 4:
            # Fuzz deserialize_type with a dict containing __type__
            # Use an empty cls_map so unknown types raise KeyError
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
            test_data = {"__type__": text}
            deserialize_type({}, test_data)

    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        IndexError,
        OverflowError,
        AssertionError,
        StopIteration,
        RecursionError,
    ):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
