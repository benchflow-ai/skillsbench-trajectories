import os
import sys

import atheris

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

import numpy as np
import torch

from minisgl.core import SamplingParams
from minisgl.message.tokenizer import (
    BaseTokenizerMsg,
    BatchTokenizerMsg,
    DetokenizeMsg,
    TokenizeMsg,
)
from minisgl.message.utils import deserialize_type, serialize_type
from minisgl.tokenizer.detokenize import _is_chinese_char, find_printable_text


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(256)

    try:
        find_printable_text(text)
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        _is_chinese_char(cp)
    except Exception:
        pass

    try:
        params = SamplingParams(
            temperature=fdp.ConsumeFloatInRange(-5.0, 5.0),
            top_k=fdp.ConsumeIntInRange(-10, 1000),
            top_p=fdp.ConsumeFloatInRange(0.0, 2.0),
            ignore_eos=fdp.ConsumeBool(),
            max_tokens=fdp.ConsumeIntInRange(0, 4096),
        )
        params.is_greedy
    except Exception:
        pass

    try:
        msg = TokenizeMsg(uid=fdp.ConsumeIntInRange(0, 1_000_000), text=text, sampling_params=params)
        encoded = BaseTokenizerMsg.encoder(msg)
        BaseTokenizerMsg.decoder(encoded)

        dmsg = DetokenizeMsg(
            uid=fdp.ConsumeIntInRange(0, 1_000_000),
            next_token=fdp.ConsumeIntInRange(-1, 100_000),
            finished=fdp.ConsumeBool(),
        )
        d_encoded = BaseTokenizerMsg.encoder(dmsg)
        BaseTokenizerMsg.decoder(d_encoded)

        batch = BatchTokenizerMsg(data=[msg, dmsg])
        b_encoded = BaseTokenizerMsg.encoder(batch)
        BaseTokenizerMsg.decoder(b_encoded)
    except Exception:
        pass

    try:
        buf = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 64))
        np_arr = np.frombuffer(buf, dtype=np.uint8)
        tensor = torch.from_numpy(np_arr.copy())
        serialized = serialize_type(tensor)
        deserialize_type({}, serialized)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
