import sys

import atheris

with atheris.instrument_imports():
    import torch
    from minisgl.core import SamplingParams
    from minisgl.message import backend as msg_backend
    from minisgl.message import frontend as msg_frontend
    from minisgl.message import tokenizer as msg_tokenizer


EXPECTED = (
    ValueError,
    TypeError,
    KeyError,
    AssertionError,
    RuntimeError,
)


def _sampling_params(fdp: atheris.FuzzedDataProvider) -> SamplingParams:
    return SamplingParams(
        temperature=fdp.ConsumeFloatInRange(-1.0, 3.0),
        top_k=fdp.ConsumeIntInRange(-1, 128),
        top_p=fdp.ConsumeFloatInRange(0.0, 1.0),
        ignore_eos=fdp.ConsumeBool(),
        max_tokens=fdp.ConsumeIntInRange(0, 256),
    )


def _text_or_chat(fdp: atheris.FuzzedDataProvider):
    if fdp.ConsumeBool():
        return fdp.ConsumeUnicodeNoSurrogates(512)
    msgs = []
    for _ in range(fdp.ConsumeIntInRange(0, 4)):
        role = fdp.ConsumeUnicodeNoSurrogates(16)
        content = fdp.ConsumeUnicodeNoSurrogates(256)
        msgs.append({"role": role, "content": content})
    return msgs


def _tokenizer_msg(fdp: atheris.FuzzedDataProvider) -> msg_tokenizer.BaseTokenizerMsg:
    msg_type = fdp.ConsumeIntInRange(0, 3)
    if msg_type == 0:
        return msg_tokenizer.TokenizeMsg(
            uid=fdp.ConsumeIntInRange(0, 1_000_000),
            text=_text_or_chat(fdp),
            sampling_params=_sampling_params(fdp),
        )
    if msg_type == 1:
        return msg_tokenizer.DetokenizeMsg(
            uid=fdp.ConsumeIntInRange(0, 1_000_000),
            next_token=fdp.ConsumeIntInRange(-1000, 1000),
            finished=fdp.ConsumeBool(),
        )
    if msg_type == 2:
        return msg_tokenizer.AbortMsg(uid=fdp.ConsumeIntInRange(0, 1_000_000))
    data = [_tokenizer_msg(fdp) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    return msg_tokenizer.BatchTokenizerMsg(data=data)


def _backend_msg(fdp: atheris.FuzzedDataProvider) -> msg_backend.BaseBackendMsg:
    msg_type = fdp.ConsumeIntInRange(0, 2)
    if msg_type == 0:
        return msg_backend.ExitMsg()
    if msg_type == 1:
        values = [fdp.ConsumeIntInRange(-1000, 1000) for _ in range(fdp.ConsumeIntInRange(0, 32))]
        tensor = torch.tensor(values, dtype=torch.int32)
        return msg_backend.UserMsg(
            uid=fdp.ConsumeIntInRange(0, 1_000_000),
            input_ids=tensor,
            sampling_params=_sampling_params(fdp),
        )
    data = [_backend_msg(fdp) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    return msg_backend.BatchBackendMsg(data=data)


def _frontend_msg(fdp: atheris.FuzzedDataProvider) -> msg_frontend.BaseFrontendMsg:
    msg_type = fdp.ConsumeIntInRange(0, 2)
    if msg_type == 0:
        return msg_frontend.UserReply(
            uid=fdp.ConsumeIntInRange(0, 1_000_000),
            incremental_output=fdp.ConsumeUnicodeNoSurrogates(512),
            finished=fdp.ConsumeBool(),
        )
    data = [_frontend_msg(fdp) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    return msg_frontend.BatchFrontendMsg(data=data)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        tmsg = _tokenizer_msg(fdp)
        encoded = msg_tokenizer.BaseTokenizerMsg.encoder(tmsg)
        msg_tokenizer.BaseTokenizerMsg.decoder(encoded)

        bmsg = _backend_msg(fdp)
        encoded_b = bmsg.encoder()
        msg_backend.BaseBackendMsg.decoder(encoded_b)

        fmsg = _frontend_msg(fdp)
        encoded_f = msg_frontend.BaseFrontendMsg.encoder(fmsg)
        msg_frontend.BaseFrontendMsg.decoder(encoded_f)
    except EXPECTED:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
