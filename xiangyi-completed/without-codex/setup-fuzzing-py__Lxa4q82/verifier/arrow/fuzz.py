import sys
import atheris

with atheris.instrument_imports():
    import datetime as _dt
    import arrow
    from arrow import parser as arrow_parser


def _fuzz_parse_strings(fdp: atheris.FuzzedDataProvider) -> None:
    text = fdp.ConsumeUnicodeNoSurrogates(64)
    if not text:
        return
    mode = fdp.ConsumeIntInRange(0, 2)
    if mode == 0:
        arrow.get(text)
    elif mode == 1:
        fmts = [
            "YYYY-MM-DD",
            "YYYY-MM-DD HH:mm:ss",
            "YYYY-MM-DDTHH:mm:ssZZ",
            "YYYY-MM-DDTHH:mm:ss.SSSZZ",
            "YYYY-MM-DDTHH:mm:ss",
        ]
        arrow.get(text, fmts[fdp.ConsumeIntInRange(0, len(fmts) - 1)])
    else:
        parser = arrow_parser.Parser()
        parser.parse(text, [
            "YYYY-MM-DD",
            "YYYY-MM-DD HH:mm:ss",
            "YYYY-MM-DDTHH:mm:ssZZ",
        ])


def _fuzz_timestamps(fdp: atheris.FuzzedDataProvider) -> None:
    ts = fdp.ConsumeIntInRange(-2208988800, 4102444800)  # 1900-2100
    if fdp.ConsumeBool():
        arrow.get(ts)
    else:
        arrow.Arrow.fromtimestamp(ts)


def _fuzz_datetime_ops(fdp: atheris.FuzzedDataProvider) -> None:
    year = fdp.ConsumeIntInRange(1, 9999)
    month = fdp.ConsumeIntInRange(1, 12)
    day = fdp.ConsumeIntInRange(1, 28)
    hour = fdp.ConsumeIntInRange(0, 23)
    minute = fdp.ConsumeIntInRange(0, 59)
    second = fdp.ConsumeIntInRange(0, 59)
    dt = _dt.datetime(year, month, day, hour, minute, second)
    arw = arrow.get(dt)
    arw.format("YYYY-MM-DD HH:mm:ss")


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    try:
        choice = fdp.ConsumeIntInRange(0, 2)
        if choice == 0:
            _fuzz_parse_strings(fdp)
        elif choice == 1:
            _fuzz_timestamps(fdp)
        else:
            _fuzz_datetime_ops(fdp)
    except (
        ValueError,
        TypeError,
        OverflowError,
        arrow_parser.ParserError,
    ):
        return


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
