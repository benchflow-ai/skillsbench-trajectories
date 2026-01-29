import sys

import atheris
import arrow


try:
    from arrow.parser import ParserError
except Exception:  # pragma: no cover - optional error type
    ParserError = Exception


def _maybe_tz(tz_value: str):
    if not tz_value:
        return None
    return tz_value


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(256)
    if not text:
        return

    choice = fdp.ConsumeIntInRange(0, 5)
    try:
        if choice == 0:
            arrow.get(text)
        elif choice == 1:
            fmt = fdp.ConsumeUnicodeNoSurrogates(64)
            if fmt:
                arrow.get(text, fmt)
            else:
                arrow.get(text)
        elif choice == 2:
            fmts = [fdp.ConsumeUnicodeNoSurrogates(32) for _ in range(3)]
            fmts = [f for f in fmts if f]
            if fmts:
                arrow.get(text, fmts)
            else:
                arrow.get(text)
        elif choice == 3:
            ts = fdp.ConsumeInt(64)
            tz = _maybe_tz(fdp.ConsumeUnicodeNoSurrogates(32))
            arrow.get(ts, tzinfo=tz)
        elif choice == 4:
            base = arrow.get(text)
            fmt = fdp.ConsumeUnicodeNoSurrogates(32)
            if fmt:
                base.format(fmt)
            base.shift(days=fdp.ConsumeIntInRange(-365, 365)).humanize()
        else:
            tz = _maybe_tz(fdp.ConsumeUnicodeNoSurrogates(32))
            arrow.now(tz).format("YYYY-MM-DD")
    except (ParserError, ValueError, TypeError, OverflowError, AssertionError):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
