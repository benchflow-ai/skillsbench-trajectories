import os
import sys

import atheris


ROOT = os.path.abspath(os.path.dirname(__file__))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from minisgl.server.args import parse_args  # noqa: E402


ATTN_BACKENDS = ["auto", "fi", "fa", "fa,fi"]
CACHE_TYPES = ["naive", "radix"]


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    args = ["--model-path", fdp.ConsumeUnicodeNoSurrogates(32) or "./dummy"]
    args += ["--dtype", fdp.PickValueInList(["float16", "bfloat16", "float32"])]

    if fdp.ConsumeBool():
        args += ["--tensor-parallel-size", str(fdp.ConsumeIntInRange(1, 8))]
    if fdp.ConsumeBool():
        args += ["--max-running-requests", str(fdp.ConsumeIntInRange(1, 64))]
    if fdp.ConsumeBool():
        args += ["--max-seq-len-override", str(fdp.ConsumeIntInRange(1, 8192))]
    if fdp.ConsumeBool():
        args += ["--memory-ratio", str(fdp.ConsumeFloatInRange(0.0, 1.0))]
    if fdp.ConsumeBool():
        args += ["--host", fdp.ConsumeUnicodeNoSurrogates(32) or "127.0.0.1"]
    if fdp.ConsumeBool():
        args += ["--port", str(fdp.ConsumeIntInRange(1, 65535))]
    if fdp.ConsumeBool():
        args += ["--cuda-graph-max-bs", str(fdp.ConsumeIntInRange(1, 32))]
    if fdp.ConsumeBool():
        args += ["--num-tokenizer", str(fdp.ConsumeIntInRange(0, 8))]
    if fdp.ConsumeBool():
        args += ["--max-prefill-length", str(fdp.ConsumeIntInRange(1, 8192))]
    if fdp.ConsumeBool():
        args += ["--num-pages", str(fdp.ConsumeIntInRange(1, 4096))]
    if fdp.ConsumeBool():
        args += ["--attention-backend", fdp.PickValueInList(ATTN_BACKENDS)]
    if fdp.ConsumeBool():
        args += ["--cache-type", fdp.PickValueInList(CACHE_TYPES)]
    if fdp.ConsumeBool():
        args += ["--shell-mode"]

    try:
        parse_args(args)
    except (SystemExit, ValueError, TypeError, RuntimeError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
