import sys

import atheris

import arrow
from arrow import parser as arrow_parser


def _safe_get(text: str, tzinfo: str | None):
    try:
        return arrow.get(text, tzinfo=tzinfo)
    except (arrow_parser.ParserError, ValueError, TypeError):
        return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(128)
    fmt = fdp.ConsumeUnicodeNoSurrogates(32)
    tz = fdp.ConsumeUnicodeNoSurrogates(32) or None
    timestamp = fdp.ConsumeIntInRange(-2208988800, 4102444800)

    parser = arrow_parser.DateTimeParser()
    if text:
        try:
            if fdp.ConsumeBool():
                parser.parse_iso(text)
            else:
                if not fmt:
                    fmt = "YYYY-MM-DD"
                parser.parse(text, fmt)
        except (arrow_parser.ParserError, arrow_parser.ParserMatchError, ValueError):
            pass

    # Exercise factory + Arrow methods
    a = None
    if text and fdp.ConsumeBool():
        a = _safe_get(text, tz if fdp.ConsumeBool() else None)
    if a is None:
        try:
            a = arrow.get(timestamp)
        except (ValueError, TypeError):
            a = None

    if a is not None:
        try:
            a.format(fmt or "YYYY-MM-DD")
        except (ValueError, KeyError):
            pass
        try:
            a.shift(days=fdp.ConsumeIntInRange(-7, 7))
        except (ValueError, OverflowError):
            pass
        try:
            a.replace(year=fdp.ConsumeIntInRange(1900, 2100))
        except (ValueError, OverflowError):
            pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
