import sys
from dataclasses import dataclass

import atheris

with atheris.instrument_imports():
    from minisgl.utils.registry import Registry

try:
    from minisgl.message import utils as msg_utils
except Exception:  # pragma: no cover - optional deps
    msg_utils = None


@dataclass
class _FuzzMsg:
    text: str
    number: int
    data: list[int]


def _registry_rounds(fdp: atheris.FuzzedDataProvider) -> None:
    reg = Registry("fuzz")
    count = fdp.ConsumeIntInRange(0, 8)
    names = []
    for _ in range(count):
        name = fdp.ConsumeUnicodeNoSurrogates(12)
        if not name:
            continue
        try:
            reg.register(name)(_FuzzMsg)
            names.append(name)
        except KeyError:
            pass
    _ = reg.supported_names()
    lookup = fdp.ConsumeUnicodeNoSurrogates(12)
    if lookup:
        try:
            _ = reg[lookup]
        except KeyError:
            pass


def _message_serde(fdp: atheris.FuzzedDataProvider) -> None:
    if msg_utils is None:
        return
    msg = _FuzzMsg(
        text=fdp.ConsumeUnicodeNoSurrogates(64),
        number=fdp.ConsumeIntInRange(-100000, 100000),
        data=[fdp.ConsumeIntInRange(-1000, 1000) for _ in range(fdp.ConsumeIntInRange(0, 16))],
    )
    encoded = msg_utils.serialize_type(msg)
    _ = msg_utils.deserialize_type({"_FuzzMsg": _FuzzMsg}, encoded)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    _registry_rounds(fdp)
    _message_serde(fdp)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
