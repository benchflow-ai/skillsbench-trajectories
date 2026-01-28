import atheris
import sys

with atheris.instrument_imports():
    import torch
    from minisgl.core import SamplingParams
    from minisgl.message import tokenizer as tokenizer_msg
    from minisgl.message import frontend as frontend_msg
    from minisgl.message import backend as backend_msg
    from minisgl.message import utils as msg_utils


def _make_sampling_params(fdp: atheris.FuzzedDataProvider) -> SamplingParams:
    return SamplingParams(
        temperature=fdp.ConsumeFloatInRange(-1.0, 2.0),
        top_k=fdp.ConsumeIntInRange(-1, 100),
        top_p=fdp.ConsumeFloatInRange(0.0, 1.0),
        ignore_eos=fdp.ConsumeBool(),
        max_tokens=fdp.ConsumeIntInRange(0, 4096),
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 4)
    try:
        if choice == 0:
            params = _make_sampling_params(fdp)
            msg = tokenizer_msg.TokenizeMsg(
                uid=fdp.ConsumeIntInRange(0, 1_000_000),
                text=fdp.ConsumeUnicodeNoSurrogates(200),
                sampling_params=params,
            )
            enc = tokenizer_msg.BaseTokenizerMsg.encoder(msg)
            tokenizer_msg.BaseTokenizerMsg.decoder(enc)
        elif choice == 1:
            msg = frontend_msg.UserReply(
                uid=fdp.ConsumeIntInRange(0, 1_000_000),
                incremental_output=fdp.ConsumeUnicodeNoSurrogates(200),
                finished=fdp.ConsumeBool(),
            )
            enc = frontend_msg.BaseFrontendMsg.encoder(msg)
            frontend_msg.BaseFrontendMsg.decoder(enc)
        elif choice == 2:
            params = _make_sampling_params(fdp)
            tensor = torch.tensor(
                [fdp.ConsumeIntInRange(0, 32000) for _ in range(fdp.ConsumeIntInRange(0, 8))],
                dtype=torch.int32,
            )
            msg = backend_msg.UserMsg(
                uid=fdp.ConsumeIntInRange(0, 1_000_000),
                input_ids=tensor,
                sampling_params=params,
            )
            enc = msg.encoder()
            backend_msg.BaseBackendMsg.decoder(enc)
        elif choice == 3:
            params = _make_sampling_params(fdp)
            _ = params.is_greedy
        else:
            # Exercise generic serialize/deserialize with nested data
            payload = {
                "value": fdp.ConsumeUnicodeNoSurrogates(100),
                "flag": fdp.ConsumeBool(),
            }
            encoded = msg_utils.serialize_type(frontend_msg.UserReply(0, "", False))
            msg_utils.deserialize_type(frontend_msg.__dict__, encoded)
            msg_utils._serialize_any(payload)
    except (AssertionError, ValueError, TypeError, RuntimeError):
        return


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
