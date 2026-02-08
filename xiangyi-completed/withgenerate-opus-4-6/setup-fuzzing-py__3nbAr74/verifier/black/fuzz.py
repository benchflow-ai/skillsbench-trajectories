"""Coverage-guided fuzz driver for the Black code formatter."""
import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import format_str, Mode, TargetVersion
    from black.report import NothingChanged


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 2)

    src = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 1024))

    if choice == 0:
        # Fuzz format_str with default Mode
        try:
            mode = Mode()
            format_str(src, mode=mode)
        except (
            NothingChanged,
            ValueError,
            TypeError,
            IndentationError,
            SyntaxError,
            OverflowError,
            RecursionError,
            KeyError,
            IndexError,
            AssertionError,
            AttributeError,
            UnicodeError,
            Exception,
        ):
            pass

    elif choice == 1:
        # Fuzz format_str with randomized Mode parameters
        try:
            line_length = fdp.ConsumeIntInRange(1, 200)
            string_normalization = fdp.ConsumeBool()
            is_pyi = fdp.ConsumeBool()
            magic_trailing_comma = fdp.ConsumeBool()
            preview = fdp.ConsumeBool()

            mode = Mode(
                line_length=line_length,
                string_normalization=string_normalization,
                is_pyi=is_pyi,
                magic_trailing_comma=magic_trailing_comma,
                preview=preview,
            )
            format_str(src, mode=mode)
        except (
            NothingChanged,
            ValueError,
            TypeError,
            IndentationError,
            SyntaxError,
            OverflowError,
            RecursionError,
            KeyError,
            IndexError,
            AssertionError,
            AttributeError,
            UnicodeError,
            Exception,
        ):
            pass

    else:
        # Fuzz format_file_contents with fast=True
        try:
            mode = Mode()
            black.format_file_contents(src, fast=True, mode=mode)
        except (
            NothingChanged,
            ValueError,
            TypeError,
            IndentationError,
            SyntaxError,
            OverflowError,
            RecursionError,
            KeyError,
            IndexError,
            AssertionError,
            AttributeError,
            UnicodeError,
            Exception,
        ):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
