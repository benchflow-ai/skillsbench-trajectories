import datetime
import sys

import atheris
import arrow
from arrow import parser as arrow_parser


_MAX_TEXT = 512
_MAX_FMT = 64


def _bounded_timestamp(value: int) -> int:
    # Clamp to a safe range for datetime.utcfromtimestamp
    return max(min(value, 4102444800), -62135596800)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(min(_MAX_TEXT, fdp.remaining_bytes()))
    fmt = fdp.ConsumeUnicodeNoSurrogates(min(_MAX_FMT, fdp.remaining_bytes()))
    tz = fdp.ConsumeUnicodeNoSurrogates(min(32, fdp.remaining_bytes()))
    ts = fdp.ConsumeIntInRange(-10**12, 10**12)

    try:
        arrow.get(text)
    except Exception:
        pass

    try:
        arrow.get(ts)
    except Exception:
        pass

    if text and fmt:
        try:
            arrow.get(text, fmt)
        except Exception:
            pass

    if text and tz:
        try:
            arrow.get(text, tzinfo=tz)
        except Exception:
            pass

    parser = arrow_parser.DateTimeParser()
    if text:
        try:
            parser.parse_iso(text)
        except Exception:
            pass
        if fmt:
            try:
                parser.parse(text, fmt)
            except Exception:
                pass

    try:
        dt = datetime.datetime.utcfromtimestamp(_bounded_timestamp(ts))
        arr = arrow.get(dt)
        fmt2 = fmt or "YYYY-MM-DD"
        try:
            arr.format(fmt2)
        except Exception:
            pass
        try:
            arr.shift(days=fdp.ConsumeIntInRange(-3650, 3650))
        except Exception:
            pass
        try:
            arr.replace(year=fdp.ConsumeIntInRange(1, 9999))
        except Exception:
            pass
        try:
            arr.floor("day")
        except Exception:
            pass
        try:
            arr.ceil("day")
        except Exception:
            pass
        try:
            arr.span("day")
        except Exception:
            pass
        try:
            arr.humanize(arrow.utcnow())
        except Exception:
            pass
        if text:
            try:
                arr.dehumanize(text)
            except Exception:
                pass
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
