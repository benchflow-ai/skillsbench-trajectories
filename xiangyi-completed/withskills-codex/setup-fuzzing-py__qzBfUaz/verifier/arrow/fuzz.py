import datetime as dt
import os
import sys

import atheris

sys.path.insert(0, os.path.dirname(__file__))

import arrow
from arrow import parser


def _rand_tz(fdp: atheris.FuzzedDataProvider):
    tz_choices = [None, "UTC", "local", "US/Pacific", "Europe/Paris", "Asia/Tokyo"]
    return tz_choices[fdp.ConsumeIntInRange(0, len(tz_choices) - 1)]


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(200)
    fmt = fdp.ConsumeUnicodeNoSurrogates(64)
    tz = _rand_tz(fdp)

    try:
        ts = fdp.ConsumeIntInRange(-2_000_000_000, 2_000_000_000)
        arrow.get(ts, tzinfo=tz)
    except Exception:
        pass

    try:
        if text:
            if fmt:
                arrow.get(text, fmt, tzinfo=tz)
            else:
                arrow.get(text, tzinfo=tz)
    except Exception:
        pass

    try:
        if text:
            parser.Parser().parse(text)
    except Exception:
        pass

    try:
        now = arrow.utcnow()
        now.format(fmt or "YYYY-MM-DD")
        now.shift(
            days=fdp.ConsumeIntInRange(-3650, 3650),
            seconds=fdp.ConsumeIntInRange(-100000, 100000),
        )
        now.replace(year=fdp.ConsumeIntInRange(1, 9999))
        now.humanize()
        if text:
            now.dehumanize(text)
    except Exception:
        pass

    try:
        start = arrow.get(fdp.ConsumeIntInRange(0, 2_000_000_000))
        end = start.shift(days=fdp.ConsumeIntInRange(0, 30))
        list(arrow.Arrow.range("day", start, end))
        list(arrow.Arrow.span_range("day", start, end))
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
