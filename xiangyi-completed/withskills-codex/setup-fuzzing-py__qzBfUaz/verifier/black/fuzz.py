import os
import sys

import atheris

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import black
from black import FileMode


TARGET_VERSIONS = [
    black.TargetVersion.PY310,
    black.TargetVersion.PY311,
    black.TargetVersion.PY312,
    black.TargetVersion.PY313,
]


def _pick_target_versions(fdp: atheris.FuzzedDataProvider):
    version = TARGET_VERSIONS[fdp.ConsumeIntInRange(0, len(TARGET_VERSIONS) - 1)]
    return {version}


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(800)
    if not src.endswith("\n"):
        src += "\n"

    mode = FileMode(
        line_length=fdp.ConsumeIntInRange(40, 140),
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
        target_versions=_pick_target_versions(fdp),
        preview=fdp.ConsumeBool(),
    )

    try:
        black.format_str(src, mode=mode)
    except Exception:
        pass

    try:
        black.format_file_contents(src, fast=fdp.ConsumeBool(), mode=mode)
    except Exception:
        pass

    try:
        black.parse_ast(src)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
