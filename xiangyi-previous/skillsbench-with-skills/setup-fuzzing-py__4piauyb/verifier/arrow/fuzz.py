import sys
import atheris
from datetime import datetime
import arrow
from arrow import parser, formatter


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(100)
    fmt = fdp.ConsumeUnicodeNoSurrogates(30)
    try:
        arrow.get(s)
    except Exception:
        pass
    # parse using Parser
    try:
        parser.Parser().parse(s)
    except Exception:
        pass
    # format with formatter
    try:
        formatter.Formatter().format(datetime.utcnow(), fmt)
    except Exception:
        pass
    # timestamp
    try:
        ts = fdp.ConsumeIntInRange(-10**12, 10**12)
        arrow.get(ts)
    except Exception:
        pass
    # tuple date
    try:
        y = fdp.ConsumeIntInRange(1, 3000)
        m = fdp.ConsumeIntInRange(1, 12)
        d = fdp.ConsumeIntInRange(1, 31)
        arrow.get((y, m, d))
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
