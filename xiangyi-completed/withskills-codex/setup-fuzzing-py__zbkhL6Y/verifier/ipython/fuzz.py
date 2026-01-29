import sys
import atheris


def _load():
    with atheris.instrument_imports():
        from IPython.core.inputtransformer2 import TransformerManager
        from IPython.core.splitinput import split_user_input
        from IPython.core.magic_arguments import argument, magic_arguments, construct_parser, parse_argstring
        from IPython.core.completer import Completer
        from IPython.core.prefilter import PrefilterManager
    return (
        TransformerManager,
        split_user_input,
        argument,
        magic_arguments,
        construct_parser,
        parse_argstring,
        Completer,
        PrefilterManager,
    )


(
    TransformerManager,
    split_user_input,
    argument,
    magic_arguments,
    construct_parser,
    parse_argstring,
    Completer,
    PrefilterManager,
) = _load()


@magic_arguments()
@argument("-o", "--option", default="x")
@argument("arg", nargs="?")
def _magic_demo(line):
    return line


_magic_demo.parser = construct_parser(_magic_demo)
_transformer = TransformerManager()
_completer = Completer()
_prefilter = PrefilterManager(shell=None)


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(400)

    try:
        choice = fdp.ConsumeIntInRange(0, 4)
        if choice == 0:
            _transformer.transform_cell(text)
        elif choice == 1:
            split_user_input(text)
        elif choice == 2:
            parse_argstring(_magic_demo, text, partial=fdp.ConsumeBool())
        elif choice == 3:
            _completer.split_line(text, cursor_pos=fdp.ConsumeIntInRange(0, len(text)))
        else:
            _prefilter.transform_line(text, continue_prompt=fdp.ConsumeBool())
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
