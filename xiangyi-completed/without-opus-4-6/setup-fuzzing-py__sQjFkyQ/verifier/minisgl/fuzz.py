import sys
import atheris


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    import msgpack
    from minisgl.message.utils import deserialize_type, _deserialize_any
    from minisgl.core import SamplingParams
    from minisgl.message.frontend import BaseFrontendMsg, UserReply, BatchFrontendMsg
    from minisgl.message.tokenizer import (
        BaseTokenizerMsg,
        DetokenizeMsg,
        TokenizeMsg,
        AbortMsg,
        BatchTokenizerMsg,
    )

    # Build a cls_map similar to what the decoders use (globals() from each module)
    frontend_cls_map = {
        "UserReply": UserReply,
        "BatchFrontendMsg": BatchFrontendMsg,
    }
    tokenizer_cls_map = {
        "DetokenizeMsg": DetokenizeMsg,
        "TokenizeMsg": TokenizeMsg,
        "AbortMsg": AbortMsg,
        "BatchTokenizerMsg": BatchTokenizerMsg,
        "SamplingParams": SamplingParams,
    }

    # Fuzz msgpack deserialization
    try:
        raw = fdp.ConsumeBytes(fdp.remaining_bytes())
        unpacked = msgpack.unpackb(raw, raw=False)
    except Exception:
        unpacked = None

    # Fuzz _deserialize_any with structured dict data
    try:
        choice = fdp.ConsumeIntInRange(0, 2)
        test_dict = {
            "__type__": fdp.ConsumeUnicodeNoSurrogates(32),
            "uid": fdp.ConsumeInt(4),
            "finished": fdp.ConsumeBool(),
        }
        if choice == 0:
            test_dict["incremental_output"] = fdp.ConsumeUnicodeNoSurrogates(64)
            _deserialize_any(frontend_cls_map, test_dict)
        elif choice == 1:
            test_dict["next_token"] = fdp.ConsumeInt(4)
            _deserialize_any(tokenizer_cls_map, test_dict)
        else:
            _deserialize_any(tokenizer_cls_map, test_dict)
    except Exception:
        pass

    # Fuzz deserialize_type directly with a UserReply-like structure
    try:
        d = {
            "__type__": "UserReply",
            "uid": fdp.ConsumeInt(4),
            "incremental_output": fdp.ConsumeUnicodeNoSurrogates(64),
            "finished": fdp.ConsumeBool(),
        }
        deserialize_type(frontend_cls_map, d)
    except Exception:
        pass

    # Fuzz deserialize_type with DetokenizeMsg
    try:
        d = {
            "__type__": "DetokenizeMsg",
            "uid": fdp.ConsumeInt(4),
            "next_token": fdp.ConsumeInt(4),
            "finished": fdp.ConsumeBool(),
        }
        deserialize_type(tokenizer_cls_map, d)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
