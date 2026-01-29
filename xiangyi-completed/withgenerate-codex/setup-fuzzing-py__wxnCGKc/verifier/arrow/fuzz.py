import sys

import atheris

with atheris.instrument_imports():
    import arrow
    from arrow import parser as arrow_parser


EXPECTED = (
    arrow_parser.ParserError,
    ValueError,
    TypeError,
    OverflowError,
)


def _maybe_parse_datetime(fdp: atheris.FuzzedDataProvider) -> "arrow.Arrow":
    text = fdp.ConsumeUnicodeNoSurrogates(128)
    if fdp.ConsumeBool() and text:
        return arrow.get(text)
    timestamp = fdp.ConsumeIntInRange(-10**12, 10**12)
    return arrow.get(timestamp)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    fmt = fdp.ConsumeUnicodeNoSurrogates(64)
    try:
        dt = _maybe_parse_datetime(fdp)
        # Exercise formatting and arithmetic.
        if fmt:
            dt.format(fmt)
        else:
            dt.format()
        dt.shift(seconds=fdp.ConsumeIntInRange(-100000, 100000))
        dt.floor("day")
        dt.ceil("day")
        dt.span("day")

        # Exercise explicit parser paths.
        parser = arrow_parser.DateTimeParser()
        text = fdp.ConsumeUnicodeNoSurrogates(64)
        if text:
            parser.parse_iso(text)
        fmt2 = fdp.ConsumeUnicodeNoSurrogates(32)
        if text and fmt2:
            parser.parse(text, fmt2)
    except EXPECTED:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
