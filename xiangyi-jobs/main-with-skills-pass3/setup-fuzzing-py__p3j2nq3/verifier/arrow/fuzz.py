import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow import parser as arrow_parser


FORMATS = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY-MM-DDTHH:mm:ssZZ",
    "YYYY-WWW-E",
    "YYYY-MM-DDTHH:mm:ss.SSSSSS",
    "HH:mm:ss",
    "YYYY-MM-DD ZZ",
]
FRAMES = ["year", "month", "day", "hour", "minute", "second", "week"]


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(200)
    fmt = FORMATS[fdp.ConsumeIntInRange(0, len(FORMATS) - 1)]
    ts = fdp.ConsumeIntInRange(-10**10, 10**10)
    tz = fdp.ConsumeUnicodeNoSurrogates(20)

    parser = arrow_parser.DateTimeParser()
    _safe_call(parser.parse_iso, s)
    _safe_call(parser.parse, s, fmt, normalize_whitespace=fdp.ConsumeBool())

    dt = None
    if fdp.ConsumeBool():
        dt = _safe_call(arrow.get, s)
    else:
        dt = _safe_call(arrow.get, ts)

    if dt is None and s:
        dt = _safe_call(arrow.get, s, fmt)

    if dt is None:
        return

    _safe_call(dt.format, fmt)
    _safe_call(dt.humanize)
    _safe_call(dt.humanize, dt.shift(days=1))

    frame = FRAMES[fdp.ConsumeIntInRange(0, len(FRAMES) - 1)]
    _safe_call(dt.floor, frame)
    _safe_call(dt.ceil, frame)
    _safe_call(dt.span, frame)

    _safe_call(
        dt.shift,
        years=fdp.ConsumeIntInRange(-10, 10),
        months=fdp.ConsumeIntInRange(-24, 24),
        days=fdp.ConsumeIntInRange(-365, 365),
        hours=fdp.ConsumeIntInRange(-72, 72),
        minutes=fdp.ConsumeIntInRange(-120, 120),
        seconds=fdp.ConsumeIntInRange(-120, 120),
        weeks=fdp.ConsumeIntInRange(-52, 52),
        microseconds=fdp.ConsumeIntInRange(-1000000, 1000000),
    )

    _safe_call(
        dt.replace,
        year=fdp.ConsumeIntInRange(1, 9999),
        month=fdp.ConsumeIntInRange(1, 12),
        day=fdp.ConsumeIntInRange(1, 28),
    )

    if tz:
        _safe_call(arrow.get, s, tzinfo=tz)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
