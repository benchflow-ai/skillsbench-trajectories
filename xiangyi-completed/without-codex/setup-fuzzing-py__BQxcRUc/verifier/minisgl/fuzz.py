import sys

import atheris
import torch

with atheris.instrument_imports(include=["minisgl"]):
    from minisgl.core import SamplingParams
    from minisgl.message import utils as msg_utils
    from minisgl.tokenizer import detokenize as detok


class Dummy:
    def __init__(self, a, b):
        self.a = a
        self.b = b


def _build_nested(fdp: atheris.FuzzedDataProvider, depth: int = 0):
    if depth > 2:
        return fdp.ConsumeUnicodeNoSurrogates(20)
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.ConsumeIntInRange(-1000, 1000)
    if choice == 1:
        return fdp.ConsumeFloat()
    if choice == 2:
        return fdp.ConsumeUnicodeNoSurrogates(40)
    if choice == 3:
        return [
            _build_nested(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        ]
    return {
        fdp.ConsumeUnicodeNoSurrogates(10): _build_nested(fdp, depth + 1)
        for _ in range(fdp.ConsumeIntInRange(0, 3))
    }


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
        detok._is_chinese_char(cp)

        text = fdp.ConsumeUnicodeNoSurrogates(200)
        detok.find_printable_text(text)

        params = SamplingParams(
            temperature=fdp.ConsumeFloat(),
            top_k=fdp.ConsumeIntInRange(-10, 10),
            top_p=fdp.ConsumeFloat(),
            ignore_eos=fdp.ConsumeBool(),
            max_tokens=fdp.ConsumeIntInRange(1, 2048),
        )
        params.is_greedy

        dummy = Dummy(_build_nested(fdp), _build_nested(fdp))
        try:
            serialized = msg_utils.serialize_type(dummy)
            if isinstance(serialized, dict) and "__type__" in serialized:
                try:
                    msg_utils.deserialize_type({"Dummy": Dummy}, serialized)
                except Exception:
                    pass
        except Exception:
            pass

        if fdp.ConsumeBool():
            vals = [fdp.ConsumeIntInRange(-10, 10) for _ in range(4)]
            tensor = torch.tensor(vals, dtype=torch.int32)
            try:
                msg_utils.serialize_type(tensor)
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
