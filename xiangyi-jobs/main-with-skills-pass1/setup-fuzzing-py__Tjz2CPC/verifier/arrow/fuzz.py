import atheris
import sys

with atheris.instrument_imports():
    import arrow
    from arrow import parser, formatter


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 5)
    text = fdp.ConsumeUnicodeNoSurrogates(200)
    ts = fdp.ConsumeIntInRange(-2_000_000_000, 2_000_000_000)

    try:
        if choice == 0:
            # parse string or timestamp
            if fdp.ConsumeBool():
                arrow.get(text, normalize_whitespace=fdp.ConsumeBool())
            else:
                arrow.get(ts)
        elif choice == 1:
            ar = arrow.get(ts)
            ar.shift(
                days=fdp.ConsumeIntInRange(-1000, 1000),
                seconds=fdp.ConsumeIntInRange(-100000, 100000),
            )
        elif choice == 2:
            ar = arrow.get(ts)
            ar.replace(
                year=fdp.ConsumeIntInRange(1, 9999),
                month=fdp.ConsumeIntInRange(1, 12),
                day=fdp.ConsumeIntInRange(1, 28),
                hour=fdp.ConsumeIntInRange(0, 23),
                minute=fdp.ConsumeIntInRange(0, 59),
                second=fdp.ConsumeIntInRange(0, 59),
            )
        elif choice == 3:
            parser.DateTimeParser().parse(text)
        elif choice == 4:
            fmt = fdp.ConsumeUnicodeNoSurrogates(64)
            formatter.DateTimeFormatter().format(arrow.get(ts).datetime, fmt)
        else:
            start = arrow.get(ts)
            end = start.shift(days=fdp.ConsumeIntInRange(0, 10))
            list(arrow.Arrow.range("day", start, end, limit=10))
            start.humanize(end)
    except (
        parser.ParserError,
        parser.ParserMatchError,
        ValueError,
        OverflowError,
        TypeError,
    ):
        return


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
