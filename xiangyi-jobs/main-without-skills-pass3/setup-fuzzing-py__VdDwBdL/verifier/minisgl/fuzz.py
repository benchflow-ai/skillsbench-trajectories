import sys

import atheris

from minisgl.core import SamplingParams
from minisgl.message.tokenizer import BatchTokenizerMsg, DetokenizeMsg, TokenizeMsg
from minisgl.message.utils import deserialize_type, serialize_type
from minisgl.tokenizer.detokenize import _is_chinese_char, find_printable_text
from minisgl.utils.misc import divide_down, divide_even, divide_up
from minisgl.utils.registry import Registry


CLS_MAP = {
    "TokenizeMsg": TokenizeMsg,
    "DetokenizeMsg": DetokenizeMsg,
    "BatchTokenizerMsg": BatchTokenizerMsg,
    "SamplingParams": SamplingParams,
}


def _consume_text(fdp, max_len: int) -> str:
    return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, max_len))


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    # Unicode helpers
    text = _consume_text(fdp, 256)
    find_printable_text(text)
    _is_chinese_char(fdp.ConsumeIntInRange(0, 0x10FFFF))

    # Message serialization round-trip
    sampling = SamplingParams(
        temperature=fdp.ConsumeIntInRange(-10, 10) / 10.0,
        top_k=fdp.ConsumeIntInRange(-1, 100),
        top_p=fdp.ConsumeIntInRange(0, 100) / 100.0,
        ignore_eos=fdp.ConsumeIntInRange(0, 1) == 1,
        max_tokens=fdp.ConsumeIntInRange(0, 2048),
    )
    msg = TokenizeMsg(
        uid=fdp.ConsumeIntInRange(0, 1_000_000),
        text=text,
        sampling_params=sampling,
    )
    batch = BatchTokenizerMsg(data=[msg])
    try:
        serialized = serialize_type(batch)
        deserialize_type(CLS_MAP, serialized)
    except (KeyError, AssertionError, ValueError, TypeError):
        pass

    # Registry behavior
    reg = Registry("thing")
    name = _consume_text(fdp, 20)
    value = fdp.ConsumeIntInRange(-1000, 1000)
    try:
        reg.register(name)(value)
        _ = reg[name]
    except KeyError:
        pass

    # Arithmetic helpers
    a = fdp.ConsumeIntInRange(-1_000_000, 1_000_000)
    b = fdp.ConsumeIntInRange(1, 1000)
    try:
        divide_even(a, b)
    except AssertionError:
        pass
    divide_up(a, b)
    divide_down(a, b)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
