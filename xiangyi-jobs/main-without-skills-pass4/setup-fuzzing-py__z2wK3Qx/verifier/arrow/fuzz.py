import sys

import atheris

with atheris.instrument_imports():
    import arrow


def _consume_tz(fdp: atheris.FuzzedDataProvider) -> str | None:
    tz = fdp.ConsumeUnicodeNoSurrogates(32).strip()
    return tz or None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)
    try:
        if choice == 0:
            text = fdp.ConsumeUnicodeNoSurrogates(200)
            if fdp.ConsumeBool():
                fmt = fdp.ConsumeUnicodeNoSurrogates(32)
                arrow.get(text, fmt)
            else:
                arrow.get(text)
        elif choice == 1:
            ts = fdp.ConsumeIntInRange(-10**11, 10**11)
            tz = _consume_tz(fdp)
            try:
                current = arrow.get(ts, tzinfo=tz)
            except Exception:
                current = arrow.get(ts)
            current.shift(
                days=fdp.ConsumeIntInRange(-4000, 4000),
                months=fdp.ConsumeIntInRange(-240, 240),
                years=fdp.ConsumeIntInRange(-200, 200),
                hours=fdp.ConsumeIntInRange(-1000, 1000),
                minutes=fdp.ConsumeIntInRange(-1000, 1000),
            )
            fmt = fdp.ConsumeUnicodeNoSurrogates(24) or "YYYY-MM-DD"
            current.format(fmt)
        elif choice == 2:
            base = arrow.utcnow()
            frame = fdp.PickValueFromList(
                ["year", "month", "week", "day", "hour", "minute", "second"]
            )
            base.span(frame, count=fdp.ConsumeIntInRange(1, 4))
        else:
            text = fdp.ConsumeUnicodeNoSurrogates(200)
            fmt = fdp.ConsumeUnicodeNoSurrogates(32)
            arrow.get(text, [fmt])
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
