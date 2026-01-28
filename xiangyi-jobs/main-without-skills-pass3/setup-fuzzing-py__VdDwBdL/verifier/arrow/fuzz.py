import sys

import atheris
import arrow
from arrow import util


FRAMES = ["year", "month", "day", "hour", "minute", "second", "week"]


def _consume_text(fdp, max_len: int) -> str:
    return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, max_len))


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    # Base Arrow instance from timestamp or now()
    try:
        ts = fdp.ConsumeIntInRange(-10_000_000_000, 10_000_000_000)
        base = arrow.get(ts)
    except Exception:
        base = arrow.utcnow()

    choice = fdp.ConsumeIntInRange(0, 5)

    if choice == 0:
        # Parse string input
        s = _consume_text(fdp, 128)
        try:
            arrow.get(s)
        except Exception:
            pass
    elif choice == 1:
        # Format with fuzzed format string
        fmt = _consume_text(fdp, 64)
        try:
            base.format(fmt)
        except Exception:
            pass
    elif choice == 2:
        # Shift/replace with fuzzed frame
        frame = FRAMES[fdp.ConsumeIntInRange(0, len(FRAMES) - 1)]
        delta = fdp.ConsumeIntInRange(-1000, 1000)
        try:
            base.shift(**{frame: delta})
        except Exception:
            pass
        try:
            base.replace(**{frame: fdp.ConsumeIntInRange(1, 28)})
        except Exception:
            pass
    elif choice == 3:
        # Floor/ceil/span
        frame = FRAMES[fdp.ConsumeIntInRange(0, len(FRAMES) - 1)]
        try:
            base.floor(frame)
            base.ceil(frame)
            base.span(frame)
        except Exception:
            pass
    elif choice == 4:
        # Humanize with other Arrow instance
        try:
            other = arrow.get(fdp.ConsumeIntInRange(-10_000_000_000, 10_000_000_000))
            base.humanize(other)
        except Exception:
            pass
    else:
        # Utility helpers
        try:
            util.normalize_timestamp(float(fdp.ConsumeIntInRange(-10_000_000_000, 10_000_000_000)))
        except Exception:
            pass
        try:
            iso_year = fdp.ConsumeIntInRange(1, 9999)
            iso_week = fdp.ConsumeIntInRange(1, 53)
            iso_day = fdp.ConsumeIntInRange(1, 7)
            util.iso_to_gregorian(iso_year, iso_week, iso_day)
        except Exception:
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
