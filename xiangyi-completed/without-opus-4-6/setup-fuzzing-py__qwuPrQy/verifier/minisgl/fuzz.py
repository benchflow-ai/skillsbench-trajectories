"""Coverage-guided fuzz driver for the Mini-SGL library.

Focuses on message serialization/deserialization and text processing
utilities that don't require GPU or model loading.
"""

import sys
sys.path.insert(0, "/app/minisgl/python")

import atheris

import msgpack
from dataclasses import dataclass
from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
from minisgl.message.utils import deserialize_type, serialize_type, _serialize_any


@dataclass
class _TestMsg:
    uid: int = 0
    text: str = ""


_CLS_MAP = {"_TestMsg": _TestMsg}


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Mini-SGL's parsing and serialization functions."""

    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        # Fuzz find_printable_text()
        text = fdp.ConsumeUnicode(fdp.remaining_bytes())
        try:
            find_printable_text(text)
        except (ValueError, IndexError, UnicodeDecodeError, OverflowError):
            pass

    elif choice == 1:
        # Fuzz _is_chinese_char() with various codepoints
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        try:
            _is_chinese_char(cp)
        except (ValueError, OverflowError):
            pass

    elif choice == 2:
        # Fuzz deserialize_type() with arbitrary dict data
        type_name = fdp.ConsumeUnicode(64)
        remaining = fdp.ConsumeUnicode(fdp.remaining_bytes())

        test_data = {
            "__type__": type_name,
            "uid": fdp.ConsumeIntInRange(-1000000, 1000000) if fdp.remaining_bytes() > 4 else 0,
            "text": remaining,
        }

        try:
            deserialize_type(_CLS_MAP, test_data)
        except (KeyError, TypeError, ValueError, AttributeError,
                OverflowError, AssertionError):
            pass

    elif choice == 3:
        # Fuzz msgpack deserialization (the IPC transport layer)
        raw_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())
        try:
            unpacked = msgpack.unpackb(raw_bytes, raw=False)
        except (msgpack.UnpackValueError, msgpack.FormatError,
                msgpack.StackError, ValueError, TypeError,
                msgpack.ExtraData):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
