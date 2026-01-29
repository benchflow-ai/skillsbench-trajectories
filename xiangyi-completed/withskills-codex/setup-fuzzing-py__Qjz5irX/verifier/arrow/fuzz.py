import atheris
import sys

import arrow
import arrow.parser


FORMATS = [
    "YYYY-MM-DD",
    "YYYY/MM/DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY-MM-DDTHH:mm:ss",
    "YYYY-MM-DDTHH:mm:ssZZ",
    "YYYY-MM-DDTHH:mm:ss.SSSZZ",
]


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    length = fdp.ConsumeIntInRange(0, 256)
    s = fdp.ConsumeUnicodeNoSurrogates(length)
    if not s:
        return

    fmt = FORMATS[fdp.ConsumeIntInRange(0, len(FORMATS) - 1)]
    try:
        dt = arrow.get(s, fmt)
        shifted = dt.shift(
            years=fdp.ConsumeIntInRange(-5, 5),
            months=fdp.ConsumeIntInRange(-12, 12),
            days=fdp.ConsumeIntInRange(-31, 31),
            hours=fdp.ConsumeIntInRange(-24, 24),
            minutes=fdp.ConsumeIntInRange(-60, 60),
        )
        _ = shifted.floor("day")
        _ = shifted.ceil("hour")
        _ = shifted.format(fmt)
    except (
        arrow.parser.ParserMatchError,
        ValueError,
        TypeError,
        OverflowError,
    ):
        pass

    try:
        parser = arrow.parser.DateTimeParser()
        _ = parser.parse(s, fmt, normalize_whitespace=True)
    except (arrow.parser.ParserMatchError, ValueError, TypeError, OverflowError):
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
