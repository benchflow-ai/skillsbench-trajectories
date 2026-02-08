"""Coverage-guided fuzz driver for the Black code formatter using atheris (LibFuzzer)."""

import atheris
import sys

# Instrument all imports so LibFuzzer can track coverage inside black and its deps.
with atheris.instrument_imports():
    import black
    from black import format_str, Mode
    from black.parsing import InvalidInput
    from black.report import NothingChanged
    from blib2to3.pgen2.tokenize import TokenError


def TestOneInput(data: bytes) -> None:
    """Fuzz target: exercise black.format_str with varied inputs and modes."""
    fdp = atheris.FuzzedDataProvider(data)

    # Consume mode flags from the fuzz data.
    line_length = fdp.ConsumeIntInRange(1, 200)
    string_normalization = fdp.ConsumeBool()
    is_pyi = fdp.ConsumeBool()
    magic_trailing_comma = fdp.ConsumeBool()
    preview = fdp.ConsumeBool()

    # Consume the remaining bytes as a Unicode source string (no surrogates).
    src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    if not src:
        return

    mode = Mode(
        line_length=line_length,
        string_normalization=string_normalization,
        is_pyi=is_pyi,
        magic_trailing_comma=magic_trailing_comma,
        preview=preview,
    )

    try:
        format_str(src, mode=mode)
    except (
        InvalidInput,
        NothingChanged,
        TokenError,
        IndentationError,
        SyntaxError,
        ValueError,
        TypeError,
    ):
        # These are expected / acceptable exceptions for invalid or
        # already-formatted input. Swallow them so the fuzzer does not
        # treat them as crashes.
        pass
    # Any other exception (e.g. AssertionError from idempotency checks,
    # IndexError, KeyError, AttributeError, RecursionError, etc.) will
    # propagate and be reported by the fuzzer as a genuine finding.


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
