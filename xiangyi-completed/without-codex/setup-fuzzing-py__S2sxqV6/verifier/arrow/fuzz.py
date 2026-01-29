import sys

import atheris

with atheris.instrument_imports():
    import arrow


def _safe_shift(base, fdp):
    kwargs = {
        "years": fdp.ConsumeIntInRange(-200, 200),
        "months": fdp.ConsumeIntInRange(-2400, 2400),
        "days": fdp.ConsumeIntInRange(-50000, 50000),
        "hours": fdp.ConsumeIntInRange(-100000, 100000),
        "minutes": fdp.ConsumeIntInRange(-100000, 100000),
        "seconds": fdp.ConsumeIntInRange(-100000, 100000),
    }
    return base.shift(**kwargs)


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 4)

    try:
        if choice == 0:
            s = fdp.ConsumeUnicodeNoSurrogates(256)
            fmt = fdp.ConsumeUnicodeNoSurrogates(32)
            if fmt:
                arrow.get(s, fmt)
            else:
                arrow.get(s)
        elif choice == 1:
            ts = fdp.ConsumeIntInRange(-2**31, 2**31 - 1)
            arrow.get(ts)
        elif choice == 2:
            year = fdp.ConsumeIntInRange(1, 9999)
            month = fdp.ConsumeIntInRange(1, 12)
            day = fdp.ConsumeIntInRange(1, 28)
            hour = fdp.ConsumeIntInRange(0, 23)
            minute = fdp.ConsumeIntInRange(0, 59)
            second = fdp.ConsumeIntInRange(0, 59)
            arrow.get(year, month, day, hour, minute, second)
        elif choice == 3:
            base = arrow.utcnow()
            shifted = _safe_shift(base, fdp)
            fmt = fdp.ConsumeUnicodeNoSurrogates(32) or "YYYY-MM-DD"
            shifted.format(fmt)
            shifted.humanize(base)
        else:
            base = arrow.utcnow()
            phrase = fdp.ConsumeUnicodeNoSurrogates(64)
            if phrase:
                base.dehumanize(phrase)
    except (ValueError, TypeError, OverflowError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
