import sys
import atheris
from minisgl.tokenizer import detokenize as detok


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    cp = fdp.ConsumeIntInRange(0, 0x10FFFF)
    detok._is_chinese_char(cp)

    text = fdp.ConsumeUnicodeNoSurrogates(200)
    detok.find_printable_text(text)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
