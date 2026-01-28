import os
import sys

import atheris

sys.path.insert(0, os.path.dirname(__file__))

import arrow  # noqa: E402
from arrow import parser  # noqa: E402

FORMATS = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYYMMDD",
    "MM/DD/YYYY",
    "DD/MM/YYYY",
    "YYYY-MM-DDTHH:mm:ss",
    "YYYY-MM-DDTHH:mm:ssZZ",
]
FRAMES = ["year", "month", "day", "hour", "minute", "second", "week", "quarter"]


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(64)
    fmt_count = fdp.ConsumeIntInRange(0, len(FORMATS))
    chosen_formats = FORMATS[:fmt_count]

    dt = None
    try:
        if chosen_formats:
            dt = arrow.get(text, chosen_formats)
        else:
            dt = arrow.get(text)
    except Exception:
        dt = None

    if dt is None:
        timestamp = fdp.ConsumeIntInRange(-2208988800, 4102444800)
        try:
            dt = arrow.get(timestamp)
        except Exception:
            return

    try:
        shift_kwargs = {
            "days": fdp.ConsumeIntInRange(-4000, 4000),
            "months": fdp.ConsumeIntInRange(-240, 240),
            "years": fdp.ConsumeIntInRange(-200, 200),
        }
        shifted = dt.shift(**shift_kwargs)
        fmt = fdp.ConsumeUnicodeNoSurrogates(32) or "YYYY-MM-DD"
        _ = shifted.format(fmt)
        _ = shifted.humanize(arrow.utcnow())
        _ = shifted.replace(year=shifted.year, month=shifted.month, day=shifted.day)
    except Exception:
        pass

    try:
        fmt = fdp.ConsumeUnicodeNoSurrogates(32) or FORMATS[0]
        _ = parser.DateTimeParser().parse(text, fmt)
    except Exception:
        pass

    try:
        frame = FRAMES[fdp.ConsumeIntInRange(0, len(FRAMES) - 1)]
        _ = dt.floor(frame)
        _ = dt.ceil(frame)
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
