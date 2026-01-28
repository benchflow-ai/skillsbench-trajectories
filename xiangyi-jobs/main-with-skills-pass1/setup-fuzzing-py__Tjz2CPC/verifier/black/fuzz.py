import atheris
import sys

with atheris.instrument_imports():
    import black


TARGET_VERSIONS = list(black.TargetVersion)


def _random_mode(fdp: atheris.FuzzedDataProvider) -> black.FileMode:
    line_length = fdp.ConsumeIntInRange(1, 200)
    target_versions = set()
    if fdp.ConsumeBool() and TARGET_VERSIONS:
        target_versions.add(TARGET_VERSIONS[fdp.ConsumeIntInRange(0, len(TARGET_VERSIONS) - 1)])
    return black.FileMode(
        line_length=line_length,
        string_normalization=fdp.ConsumeBool(),
        is_pyi=fdp.ConsumeBool(),
        target_versions=target_versions,
        preview=fdp.ConsumeBool(),
        magic_trailing_comma=fdp.ConsumeBool(),
    )


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(500)
    mode = _random_mode(fdp)
    try:
        if fdp.ConsumeBool():
            black.format_str(src, mode=mode)
        else:
            black.format_file_contents(src, fast=fdp.ConsumeBool(), mode=mode)
        if fdp.ConsumeBool():
            black.parsing.parse_ast(src)
        if fdp.ConsumeBool():
            black.parsing.lib2to3_parse(src)
    except (
        black.InvalidInput,
        black.NothingChanged,
        black.ASTSafetyError,
        ValueError,
        SyntaxError,
        TypeError,
    ):
        return


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
