import os
import sys
import tempfile

import atheris

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import black  # noqa: E402
from black import files  # noqa: E402


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(512)
    line_length = fdp.ConsumeIntInRange(40, 140)
    mode = black.Mode(
        line_length=line_length,
        string_normalization=fdp.ConsumeBool(),
        magic_trailing_comma=fdp.ConsumeBool(),
        preview=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
    )

    try:
        _ = black.format_str(src, mode=mode)
    except Exception:
        pass

    try:
        _ = black.format_file_contents(src, fast=fdp.ConsumeBool(), mode=mode)
    except Exception:
        pass

    toml_text = fdp.ConsumeUnicodeNoSurrogates(256)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".toml") as tmp:
            tmp.write(toml_text)
            tmp_path = tmp.name
        try:
            _ = files.parse_pyproject_toml(tmp_path)
        except Exception:
            pass
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
