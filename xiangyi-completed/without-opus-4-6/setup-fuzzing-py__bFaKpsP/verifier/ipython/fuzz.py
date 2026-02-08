"""Coverage-guided fuzzer for IPython's input transformation pipeline."""

import sys
import atheris


def TestOneInput(data):
    """Fuzz target for IPython's input transformers."""
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
    if not text:
        return

    from IPython.core.inputtransformer2 import (
        TransformerManager,
        EscapedCommand,
        MagicAssign,
        SystemAssign,
        HelpEnd,
        make_tokens_by_line,
        cell_magic,
        leading_empty_lines,
        leading_indent,
    )
    from IPython.core.splitinput import split_user_input

    tm = TransformerManager()

    # Fuzz the main transform_cell entry point
    try:
        tm.transform_cell(text)
    except Exception:
        pass

    # Fuzz split_user_input with individual lines
    for line in text.splitlines():
        try:
            split_user_input(line)
        except Exception:
            pass

    # Fuzz tokenization
    lines = text.splitlines(True)
    if lines:
        try:
            tokens = make_tokens_by_line(lines)
        except Exception:
            pass

        # Fuzz cell magic transform
        try:
            cell_magic(lines)
        except Exception:
            pass

        # Fuzz cleanup transforms
        try:
            leading_empty_lines(lines)
        except Exception:
            pass

        try:
            leading_indent(lines)
        except Exception:
            pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
