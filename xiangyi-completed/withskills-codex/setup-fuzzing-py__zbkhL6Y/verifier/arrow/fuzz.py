import sys
import atheris


def _load():
    with atheris.instrument_imports():
        import arrow
        from arrow import util
    return arrow, util


arrow, util = _load()


FRAMES = ["year", "month", "week", "day", "hour", "minute", "second"]


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(200)
    fmt = fdp.ConsumeUnicodeNoSurrogates(40)
    ts = fdp.ConsumeInt(64)
    frame = FRAMES[fdp.ConsumeIntInRange(0, len(FRAMES) - 1)]

    try:
        choice = fdp.ConsumeIntInRange(0, 6)
        if choice == 0:
            arrow.get(s)
        elif choice == 1:
            arrow.get(ts)
        elif choice == 2:
            arrow.Arrow.fromtimestamp(ts / 1000.0)
        elif choice == 3:
            arrow.Arrow.strptime(s, fmt or "YYYY-MM-DD")
        elif choice == 4:
            base = arrow.get(s) if s else arrow.utcnow()
            base.shift(days=fdp.ConsumeIntInRange(-1000, 1000))
            base.floor(frame)
            base.ceil(frame)
        elif choice == 5:
            util.iso_to_gregorian(
                fdp.ConsumeIntInRange(1, 9999),
                fdp.ConsumeIntInRange(1, 53),
                fdp.ConsumeIntInRange(1, 7),
            )
        else:
            util.normalize_timestamp(float(ts))
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
