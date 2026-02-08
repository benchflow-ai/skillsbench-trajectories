"""Coverage-guided fuzz driver for Mini-SGLang using Atheris (LibFuzzer)."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for minisgl's parsing and deserialization functions."""
    fdp = atheris.FuzzedDataProvider(data)

    # Import targets - use only pure Python functions that don't need GPU
    try:
        from minisgl.env import _PARSE_MEM_BYTES
        from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
    except ImportError:
        return

    # Fuzz _PARSE_MEM_BYTES - memory size string parser
    mem_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 64))
    try:
        _PARSE_MEM_BYTES(mem_str)
    except Exception:
        pass

    # Fuzz find_printable_text - streaming output text processing
    text_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 256))
    try:
        find_printable_text(text_str)
    except Exception:
        pass

    # Fuzz _is_chinese_char - CJK codepoint detection
    codepoint = fdp.ConsumeIntInRange(0, 0x10FFFF)
    try:
        _is_chinese_char(codepoint)
    except Exception:
        pass

    # Fuzz deserialize_type with a fuzzed dict
    try:
        from minisgl.message.utils import deserialize_type
        # Create a fuzzed dict simulating incoming network message
        type_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
        fuzzed_dict = {"__type__": type_name}
        # Add some random key-value pairs
        num_keys = fdp.ConsumeIntInRange(0, 5)
        for _ in range(num_keys):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 16))
            val_choice = fdp.ConsumeIntInRange(0, 3)
            if val_choice == 0:
                fuzzed_dict[key] = fdp.ConsumeIntInRange(-1000, 1000)
            elif val_choice == 1:
                fuzzed_dict[key] = fdp.ConsumeFloat()
            elif val_choice == 2:
                fuzzed_dict[key] = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
            else:
                fuzzed_dict[key] = fdp.ConsumeBool()
        deserialize_type({}, fuzzed_dict)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
