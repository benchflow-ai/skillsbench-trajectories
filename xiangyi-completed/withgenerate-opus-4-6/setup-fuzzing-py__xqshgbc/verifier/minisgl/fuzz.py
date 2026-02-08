"""Coverage-guided fuzz driver for MiniSGL pure-Python components.

Focuses on components that don't require GPU/CUDA:
- SamplingParams validation
- Text processing utilities (find_printable_text, _is_chinese_char)
- Message serialization/deserialization
"""
import atheris
import sys

# Import torch first without instrumentation (too large)
import torch  # noqa: F401 - needed by minisgl.core

# Only instrument the minisgl modules we care about
import minisgl.core
import minisgl.tokenizer.detokenize
import minisgl.message.utils
atheris.instrument_func(minisgl.core.SamplingParams.__init__)
atheris.instrument_func(minisgl.tokenizer.detokenize.find_printable_text)
atheris.instrument_func(minisgl.tokenizer.detokenize._is_chinese_char)
atheris.instrument_func(minisgl.message.utils._serialize_any)
atheris.instrument_func(minisgl.message.utils.deserialize_type)
atheris.instrument_func(minisgl.message.utils.serialize_type)

from minisgl.core import SamplingParams
from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
from minisgl.message.utils import _serialize_any, deserialize_type, serialize_type


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    choice = fdp.ConsumeIntInRange(0, 4)

    if choice == 0:
        # Fuzz SamplingParams creation and is_greedy property
        temperature = fdp.ConsumeFloatInRange(-100.0, 100.0)
        top_k = fdp.ConsumeIntInRange(-1, 10000)
        top_p = fdp.ConsumeFloatInRange(-1.0, 2.0)
        max_tokens = fdp.ConsumeIntInRange(0, 100000)
        try:
            params = SamplingParams(
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                ignore_eos=fdp.ConsumeBool(),
                max_tokens=max_tokens,
            )
            _ = params.is_greedy
        except (ValueError, TypeError, OverflowError):
            pass

    elif choice == 1:
        # Fuzz find_printable_text
        text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
        try:
            find_printable_text(text)
        except (ValueError, TypeError, IndexError):
            pass

    elif choice == 2:
        # Fuzz _is_chinese_char with arbitrary codepoints
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        try:
            _is_chinese_char(cp)
        except (ValueError, TypeError, OverflowError):
            pass

    elif choice == 3:
        # Fuzz _serialize_any with random nested structures
        depth = fdp.ConsumeIntInRange(0, 5)
        obj = _build_random_obj(fdp, depth)
        try:
            _serialize_any(obj)
        except (ValueError, TypeError, OverflowError, AttributeError,
                KeyError, RecursionError, AssertionError):
            pass

    elif choice == 4:
        # Fuzz deserialize_type with random dict data
        type_name = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
        num_fields = fdp.ConsumeIntInRange(0, 5)
        data = {"__type__": type_name}
        for _ in range(num_fields):
            key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 16))
            val = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
            data[key] = val
        try:
            deserialize_type({}, data)
        except (ValueError, TypeError, KeyError, AttributeError,
                OverflowError, AssertionError):
            pass


def _build_random_obj(fdp, depth):
    """Build a random nested Python object for serialization testing."""
    if depth <= 0 or fdp.remaining_bytes() < 4:
        t = fdp.ConsumeIntInRange(0, 4)
        if t == 0:
            return fdp.ConsumeIntInRange(-1000, 1000)
        elif t == 1:
            return fdp.ConsumeFloat()
        elif t == 2:
            return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
        elif t == 3:
            return None
        else:
            return fdp.ConsumeBool()

    container_type = fdp.ConsumeIntInRange(0, 1)
    size = fdp.ConsumeIntInRange(0, 3)
    if container_type == 0:
        return [_build_random_obj(fdp, depth - 1) for _ in range(size)]
    else:
        return {
            fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(1, 8)):
                _build_random_obj(fdp, depth - 1)
            for _ in range(size)
        }


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
