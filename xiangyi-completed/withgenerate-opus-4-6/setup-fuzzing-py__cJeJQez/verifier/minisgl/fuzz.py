"""Coverage-guided fuzz driver for the Mini-SGLang library.

Targets:
- minisgl.tokenizer.detokenize: find_printable_text, _is_chinese_char
- minisgl.message.utils: serialize/deserialize functions
"""
import sys
import atheris

# Use instrument_all() instead of instrument_imports() to avoid
# instrumenting the entire torch/numpy dependency tree during import
atheris.instrument_all()

from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
from minisgl.message.utils import (
    deserialize_type,
    _deserialize_any,
    _serialize_any,
)


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz find_printable_text with Unicode strings
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if text:
                find_printable_text(text)

        elif choice == 1:
            # Fuzz _is_chinese_char with codepoints
            cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
            _is_chinese_char(cp)

        elif choice == 2:
            # Fuzz _deserialize_any with structured data
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            _deserialize_any({}, text)

        else:
            # Fuzz _serialize_any with various types
            sub = fdp.ConsumeIntInRange(0, 3)
            if sub == 0:
                val = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            elif sub == 1:
                val = fdp.ConsumeInt(4)
            elif sub == 2:
                val = fdp.ConsumeFloat()
            else:
                val = fdp.ConsumeBool()
            _serialize_any(val)

    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
