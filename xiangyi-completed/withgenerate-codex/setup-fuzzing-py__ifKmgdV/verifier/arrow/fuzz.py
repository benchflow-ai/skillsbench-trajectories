import sys
import datetime

import atheris
from atheris import FuzzedDataProvider

import arrow
from arrow import parser as arrow_parser


def _bounded_frame(fdp: FuzzedDataProvider) -> str:
    frames = ["year", "month", "day", "hour", "minute", "second"]
    return frames[fdp.ConsumeIntInRange(0, len(frames) - 1)]


def TestOneInput(data: bytes) -> None:
    fdp = FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(128)
    fmt = fdp.ConsumeUnicodeNoSurrogates(64)

    base = arrow.get(0)
    try:
        dt = arrow.get(s)
    except (ValueError, TypeError, OverflowError):
        dt = base

    # Formatting
    try:
        dt.format(fmt)
    except (ValueError, TypeError):
        pass

    # Parser APIs
    try:
        if fmt:
            arrow_parser.DateTimeParser().parse(s, fmt)
        arrow_parser.DateTimeParser().parse_iso(s)
    except (ValueError, TypeError, OverflowError):
        pass

    # Date arithmetic
    shift_kwargs = {
        "years": fdp.ConsumeIntInRange(-10, 10),
        "months": fdp.ConsumeIntInRange(-24, 24),
        "days": fdp.ConsumeIntInRange(-31, 31),
        "hours": fdp.ConsumeIntInRange(-48, 48),
        "minutes": fdp.ConsumeIntInRange(-120, 120),
        "seconds": fdp.ConsumeIntInRange(-120, 120),
    }
    try:
        dt.shift(**shift_kwargs)
    except (ValueError, OverflowError):
        pass

    replace_kwargs = {
        "year": fdp.ConsumeIntInRange(1970, 2038),
        "month": fdp.ConsumeIntInRange(1, 12),
        "day": fdp.ConsumeIntInRange(1, 28),
        "hour": fdp.ConsumeIntInRange(0, 23),
        "minute": fdp.ConsumeIntInRange(0, 59),
        "second": fdp.ConsumeIntInRange(0, 59),
    }
    try:
        dt.replace(**replace_kwargs)
    except (ValueError, OverflowError):
        pass

    # Span API
    frame = _bounded_frame(fdp)
    try:
        dt.span(frame)
    except (ValueError, OverflowError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
