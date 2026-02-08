import sys
import atheris


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    if not s:
        return

    try:
        if choice == 0:
            # Fuzz split_user_input
            split_user_input(s)
        elif choice == 1:
            # Fuzz the input transformer functions
            lines = s.splitlines(True)
            if lines:
                cell_magic(lines)
        elif choice == 2:
            # Fuzz arg_split
            arg_split(s, posix=False, strict=False)
            arg_split(s, posix=True, strict=False)
        elif choice == 3:
            # Fuzz line_at_cursor
            cursor_pos = fdp.ConsumeIntInRange(0, len(s))
            line_at_cursor(s, cursor_pos)
    except (
        ValueError,
        TypeError,
        IndexError,
        KeyError,
        AttributeError,
        SyntaxError,
        OverflowError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        RuntimeError,
        RecursionError,
    ):
        pass


def main():
    atheris.instrument_all()
    global split_user_input, cell_magic, arg_split, line_at_cursor
    from IPython.core.splitinput import split_user_input as _split_user_input
    from IPython.core.inputtransformer2 import cell_magic as _cell_magic
    from IPython.utils._process_common import arg_split as _arg_split
    from IPython.utils.tokenutil import line_at_cursor as _line_at_cursor
    split_user_input = _split_user_input
    cell_magic = _cell_magic
    arg_split = _arg_split
    line_at_cursor = _line_at_cursor
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
