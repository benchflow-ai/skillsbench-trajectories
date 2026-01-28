import sys
import atheris

with atheris.instrument_imports():
    import torch
    from minisgl.core import SamplingParams
    from minisgl.message import frontend as msg_frontend
    from minisgl.message import tokenizer as msg_tokenizer
    from minisgl.message import utils as msg_utils


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _make_tensor(fdp: atheris.FuzzedDataProvider) -> torch.Tensor:
    size = fdp.ConsumeIntInRange(0, 32)
    values = [fdp.ConsumeIntInRange(-128, 127) for _ in range(size)]
    return torch.tensor(values, dtype=torch.int32)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    params = SamplingParams(
        temperature=fdp.ConsumeFloat(),
        top_k=fdp.ConsumeIntInRange(-10, 100),
        top_p=fdp.ConsumeFloat(),
        ignore_eos=fdp.ConsumeBool(),
        max_tokens=fdp.ConsumeIntInRange(0, 2048),
    )

    if fdp.ConsumeBool():
        text = fdp.ConsumeUnicodeNoSurrogates(200)
    else:
        items = []
        for _ in range(fdp.ConsumeIntInRange(0, 3)):
            items.append(
                {
                    "role": fdp.ConsumeUnicodeNoSurrogates(10),
                    "content": fdp.ConsumeUnicodeNoSurrogates(100),
                }
            )
        text = items

    tok_msg = msg_tokenizer.TokenizeMsg(
        uid=fdp.ConsumeIntInRange(0, 1_000_000),
        text=text,
        sampling_params=params,
    )
    tok_dict = msg_tokenizer.BaseTokenizerMsg.encoder(tok_msg)
    _safe_call(msg_tokenizer.BaseTokenizerMsg.decoder, tok_dict)

    detok_msg = msg_tokenizer.DetokenizeMsg(
        uid=fdp.ConsumeIntInRange(0, 1_000_000),
        next_token=fdp.ConsumeIntInRange(-10_000, 10_000),
        finished=fdp.ConsumeBool(),
    )
    detok_dict = msg_tokenizer.BaseTokenizerMsg.encoder(detok_msg)
    _safe_call(msg_tokenizer.BaseTokenizerMsg.decoder, detok_dict)

    reply_msg = msg_frontend.UserReply(
        uid=fdp.ConsumeIntInRange(0, 1_000_000),
        incremental_output=fdp.ConsumeUnicodeNoSurrogates(200),
        finished=fdp.ConsumeBool(),
    )
    reply_dict = msg_frontend.BaseFrontendMsg.encoder(reply_msg)
    _safe_call(msg_frontend.BaseFrontendMsg.decoder, reply_dict)

    tensor = _make_tensor(fdp)
    _safe_call(msg_utils.serialize_type, tensor)

    tensor_dict = {
        "__type__": "Tensor",
        "buffer": tensor.numpy().tobytes(),
        "dtype": str(tensor.dtype),
    }
    _safe_call(msg_utils.deserialize_type, {"Tensor": torch.Tensor}, tensor_dict)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
