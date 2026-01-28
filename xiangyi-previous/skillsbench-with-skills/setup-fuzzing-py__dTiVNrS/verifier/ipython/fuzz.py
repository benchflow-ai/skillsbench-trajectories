import os
import sys

import atheris

sys.path.insert(0, os.path.dirname(__file__))

from IPython.core import inputtransformer2, splitinput  # noqa: E402
from IPython.utils import text as text_utils  # noqa: E402


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cell = fdp.ConsumeUnicodeNoSurrogates(512)

    try:
        transformer = inputtransformer2.TransformerManager()
        _ = transformer.transform_cell(cell)
    except Exception:
        transformer = None

    if transformer is not None:
        try:
            for line in cell.splitlines()[:3]:
                _ = transformer.transform_cell_line(line)
        except Exception:
            pass

    try:
        _ = splitinput.split_user_input(cell)
        _ = splitinput.LineInfo(cell)
    except Exception:
        pass

    try:
        _ = text_utils.indent(
            cell,
            nspaces=fdp.ConsumeIntInRange(0, 8),
            ntabs=fdp.ConsumeIntInRange(0, 2),
            flatten=fdp.ConsumeBool(),
        )
        _ = text_utils.dedent(cell)
        _ = text_utils.strip_email_quotes(cell)
        mark = fdp.ConsumeUnicodeNoSurrogates(1) or "*"
        _ = text_utils.marquee(cell[:20], width=fdp.ConsumeIntInRange(10, 80), mark=mark)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
