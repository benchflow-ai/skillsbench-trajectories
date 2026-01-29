import sys
import atheris

with atheris.instrument_imports():
    import msgpack
    import torch
    from minisgl.message import utils as msg_utils


class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _fuzz_serialize_payload(fdp: atheris.FuzzedDataProvider) -> None:
    raw = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))
    try:
        payload = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    except Exception:
        return
    msg_utils._serialize_any(payload)


def _fuzz_tensor_roundtrip(fdp: atheris.FuzzedDataProvider) -> None:
    length = fdp.ConsumeIntInRange(0, 64)
    values = [fdp.ConsumeIntInRange(-1000, 1000) for _ in range(length)]
    tensor = torch.tensor(values, dtype=torch.int64)
    packed = msg_utils.serialize_type(tensor)
    msg_utils.deserialize_type({}, packed)


def _fuzz_custom_type(fdp: atheris.FuzzedDataProvider) -> None:
    obj = Dummy(
        value=fdp.ConsumeIntInRange(-1000, 1000),
        text=fdp.ConsumeUnicodeNoSurrogates(32),
        blob=fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 32)),
    )
    packed = msg_utils.serialize_type(obj)
    msg_utils.deserialize_type({"Dummy": Dummy}, packed)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        choice = fdp.ConsumeIntInRange(0, 2)
        if choice == 0:
            _fuzz_serialize_payload(fdp)
        elif choice == 1:
            _fuzz_tensor_roundtrip(fdp)
        else:
            _fuzz_custom_type(fdp)
    except (AssertionError, ValueError, TypeError, KeyError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
