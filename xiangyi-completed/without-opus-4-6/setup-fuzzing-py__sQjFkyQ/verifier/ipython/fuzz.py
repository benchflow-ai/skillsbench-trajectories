import sys
import atheris


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    from IPython.core.splitinput import split_user_input
    from IPython.core.inputtransformer2 import TransformerManager
    from IPython.utils._process_common import arg_split

    # Fuzz split_user_input()
    try:
        split_user_input(s)
    except Exception:
        pass

    # Fuzz TransformerManager().transform_cell()
    try:
        manager = TransformerManager()
        manager.transform_cell(s)
    except Exception:
        pass

    # Fuzz arg_split()
    try:
        arg_split(s)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
