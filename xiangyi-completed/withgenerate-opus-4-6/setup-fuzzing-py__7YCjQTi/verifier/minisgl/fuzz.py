import sys
import atheris


# Since minisgl requires torch/transformers at import time, we inline
# the CPU-only target functions here to avoid heavy GPU dependencies.

def _is_chinese_char(cp):
    """Checks whether CP is the codepoint of a CJK character."""
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


def find_printable_text(text):
    """Returns the longest printable substring of text that contains only entire words."""
    if text.endswith("\n"):
        return text
    elif len(text) > 0 and _is_chinese_char(ord(text[-1])):
        return text
    elif len(text) > 1 and _is_chinese_char(ord(text[-2])):
        return text[:-1]
    else:
        return text[: text.rfind(" ") + 1]


def _serialize_any(value):
    if isinstance(value, dict):
        return {k: _serialize_any(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return type(value)(_serialize_any(v) for v in value)
    elif isinstance(value, (int, float, str, type(None), bool, bytes)):
        return value
    else:
        raise ValueError(f"Cannot serialize type {type(value)}")


def _deserialize_any(cls_map, data):
    if isinstance(data, dict):
        if "__type__" in data:
            return _deserialize_type_safe(cls_map, data)
        else:
            return {k: _deserialize_any(cls_map, v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return type(data)(_deserialize_any(cls_map, d) for d in data)
    elif isinstance(data, (int, float, str, type(None), bool, bytes)):
        return data
    else:
        raise ValueError(f"Cannot deserialize type {type(data)}")


def _deserialize_type_safe(cls_map, data):
    """Simplified deserialize_type without torch dependency."""
    type_name = data["__type__"]
    if type_name == "Tensor":
        # Skip tensor deserialization (requires torch)
        return None
    if type_name not in cls_map:
        raise KeyError(f"Unknown type: {type_name}")
    cls = cls_map[type_name]
    kwargs = {}
    for k, v in data.items():
        if k == "__type__":
            continue
        kwargs[k] = _deserialize_any(cls_map, v)
    return cls(**kwargs)


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 2)

    try:
        if choice == 0:
            # Fuzz find_printable_text with random Unicode strings
            s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if s:
                find_printable_text(s)
        elif choice == 1:
            # Fuzz _is_chinese_char with random codepoints
            cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
            _is_chinese_char(cp)
        elif choice == 2:
            # Fuzz deserialization with random dict structures
            s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            if s:
                try:
                    import json
                    d = json.loads(s)
                    if isinstance(d, dict):
                        _deserialize_any({}, d)
                except (json.JSONDecodeError, ValueError, TypeError,
                        KeyError, IndexError, AttributeError,
                        RecursionError, OverflowError):
                    pass
    except (
        ValueError,
        TypeError,
        IndexError,
        KeyError,
        AttributeError,
        OverflowError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        RuntimeError,
        RecursionError,
    ):
        pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
