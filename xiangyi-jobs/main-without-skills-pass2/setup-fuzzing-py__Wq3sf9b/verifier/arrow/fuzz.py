import sys
import atheris
import arrow
from arrow import parser as arrow_parser


def _try_parse_datetime(fdp: atheris.FuzzedDataProvider) -> None:
    dt_str = fdp.ConsumeUnicodeNoSurrogates(64)
    fmt = fdp.ConsumeUnicodeNoSurrogates(32)
    parser = arrow_parser.DateTimeParser()
    try:
        parser.parse(dt_str, fmt)
    except (ValueError, TypeError, OverflowError, arrow_parser.ParserError):
        return


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)

    if choice == 0:
        s = fdp.ConsumeUnicodeNoSurrogates(64)
        fmt = fdp.ConsumeUnicodeNoSurrogates(32)
        try:
            arrow.get(s, fmt)
        except (ValueError, TypeError, OverflowError, arrow_parser.ParserError):
            return
    elif choice == 1:
        s = fdp.ConsumeUnicodeNoSurrogates(64)
        try:
            arrow.get(s)
        except (ValueError, TypeError, OverflowError, arrow_parser.ParserError):
            return
    elif choice == 2:
        ts = fdp.ConsumeIntInRange(-(2**31), 2**31 - 1)
        try:
            arrow.get(ts)
        except (ValueError, TypeError, OverflowError):
            return
    else:
        fmt = fdp.ConsumeUnicodeNoSurrogates(32)
        try:
            arrow.utcnow().format(fmt)
        except (ValueError, TypeError, OverflowError):
            return

    if fdp.remaining_bytes() > 0:
        _try_parse_datetime(fdp)


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
