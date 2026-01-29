import sys

import atheris
import black


ALIASED_TARGET_VERSIONS = [
    black.TargetVersion.PY37,
    black.TargetVersion.PY38,
    black.TargetVersion.PY39,
    black.TargetVersion.PY310,
    black.TargetVersion.PY311,
]


def _build_mode(fdp: atheris.FuzzedDataProvider) -> black.Mode:
    target_versions = set()
    if fdp.ConsumeBool():
        target_versions.add(fdp.PickValueInList(ALIASED_TARGET_VERSIONS))
    if fdp.ConsumeBool():
        target_versions.add(fdp.PickValueInList(ALIASED_TARGET_VERSIONS))
    return black.Mode(
        target_versions=target_versions,
        line_length=fdp.ConsumeIntInRange(20, 200),
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
        is_ipynb=fdp.ConsumeBool(),
        preview=fdp.ConsumeBool(),
        unstable=fdp.ConsumeBool(),
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(512)
    if not src:
        return

    mode = _build_mode(fdp)
    try:
        if fdp.ConsumeBool():
            black.format_str(src, mode=mode)
        else:
            black.format_file_contents(src, fast=fdp.ConsumeBool(), mode=mode)
    except (
        black.NothingChanged,
        black.InvalidInput,
        black.ASTSafetyError,
        ValueError,
        TypeError,
    ):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
