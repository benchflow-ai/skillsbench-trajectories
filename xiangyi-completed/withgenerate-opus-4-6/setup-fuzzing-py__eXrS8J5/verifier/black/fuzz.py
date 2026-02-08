import atheris
import sys
from tokenize import TokenError

with atheris.instrument_imports():
    import black
    from black import Mode, TargetVersion
    from black.parsing import InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    source = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not source:
        return

    # Fuzz black.format_str() - the main entry point
    mode = Mode(
        target_versions={TargetVersion.PY311},
        line_length=88,
    )
    try:
        black.format_str(source, mode=mode)
    except (
        InvalidInput,
        ValueError,
        TypeError,
        IndexError,
        KeyError,
        AttributeError,
        RecursionError,
        TokenError,
        IndentationError,
        SyntaxError,
        UnicodeDecodeError,
        AssertionError,
    ):
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
