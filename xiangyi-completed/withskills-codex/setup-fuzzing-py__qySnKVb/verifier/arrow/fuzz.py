import sys

import atheris

with atheris.instrument_imports():
    import arrow


FORMAT_CHOICES = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY-MM-DDTHH:mm:ssZZ",
    "YYYY-MM-DDTHH:mm:ss.SSSZZ",
    "ddd, MMM D, YYYY",
    "YYYYMMDD",
]
TZ_CHOICES = ["UTC", "US/Pacific", "Europe/London", "Asia/Tokyo", "Etc/GMT+3"]


def _consume_arrow(fdp: atheris.FuzzedDataProvider) -> arrow.Arrow | None:
    mode = fdp.ConsumeIntInRange(0, 2)
    try:
        if mode == 0:
            ts = fdp.ConsumeIntInRange(-2208988800, 4102444800)
            return arrow.get(ts)
        if mode == 1:
            ts = fdp.ConsumeFloat()
            return arrow.get(ts)
        text = fdp.ConsumeUnicodeNoSurrogates(64)
        if fdp.ConsumeBool():
            fmt = fdp.PickValueInList(FORMAT_CHOICES)
            return arrow.get(text, fmt)
        return arrow.get(text)
    except (ValueError, OverflowError, arrow.parser.ParserError):
        return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    base = _consume_arrow(fdp)
    if base is None:
        return

    try:
        shifted = base.shift(
            years=fdp.ConsumeIntInRange(-50, 50),
            months=fdp.ConsumeIntInRange(-120, 120),
            days=fdp.ConsumeIntInRange(-1000, 1000),
            hours=fdp.ConsumeIntInRange(-5000, 5000),
            seconds=fdp.ConsumeIntInRange(-100000, 100000),
        )
        tz = fdp.PickValueInList(TZ_CHOICES)
        shifted = shifted.to(tz)
        fmt = fdp.PickValueInList(FORMAT_CHOICES)
        _ = shifted.format(fmt)
        end = shifted.shift(days=fdp.ConsumeIntInRange(0, 30))
        _ = list(arrow.Arrow.span_range("day", shifted, end))
    except Exception:
        # Let unexpected exceptions surface in the fuzzer.
        raise


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
