import sys

import atheris

with atheris.instrument_imports():
    import datetime as _dt

    import arrow
    from arrow import parser as arrow_parser


def _consume_datetime(fdp: atheris.FuzzedDataProvider) -> _dt.datetime:
    year = fdp.ConsumeIntInRange(1, 9999)
    month = fdp.ConsumeIntInRange(1, 12)
    # Keep day in a safe range to avoid invalid month/day combinations.
    day = fdp.ConsumeIntInRange(1, 28)
    hour = fdp.ConsumeIntInRange(0, 23)
    minute = fdp.ConsumeIntInRange(0, 59)
    second = fdp.ConsumeIntInRange(0, 59)
    microsecond = fdp.ConsumeIntInRange(0, 999999)
    return _dt.datetime(year, month, day, hour, minute, second, microsecond)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 5)
    text = fdp.ConsumeUnicodeNoSurrogates(128)

    try:
        if choice == 0:
            arrow.get(text)
        elif choice == 1:
            fmt = fdp.ConsumeUnicodeNoSurrogates(32)
            arrow.get(text, fmt)
        elif choice == 2:
            ts = fdp.ConsumeFloat()
            arrow.Arrow.fromtimestamp(ts)
        elif choice == 3:
            ordinal = fdp.ConsumeIntInRange(1, 4000000)
            arrow.Arrow.fromordinal(ordinal)
        elif choice == 4:
            dt = _consume_datetime(fdp)
            arrow.Arrow.fromdatetime(dt)
        else:
            parser = arrow_parser.DateTimeParser()
            parser.parse(text)
    except (arrow_parser.ParserError, ValueError, OverflowError, TypeError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
