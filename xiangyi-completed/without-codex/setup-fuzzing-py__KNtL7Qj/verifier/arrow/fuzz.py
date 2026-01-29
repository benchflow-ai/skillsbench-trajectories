import sys
import atheris

with atheris.instrument_imports():
    import arrow
    from arrow import parser as arrow_parser
    from arrow import locales as arrow_locales


def _safe_get(text: str, fmt: str | None = None, tzinfo: str | None = None):
    try:
        if fmt is None:
            return arrow.get(text, tzinfo=tzinfo)
        return arrow.get(text, fmt, tzinfo=tzinfo)
    except (ValueError, TypeError, OverflowError, arrow_parser.ParserError):
        return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(200)
    if not text:
        return

    formats = [
        "YYYY-MM-DD",
        "YYYYMMDD",
        "YYYY-MM-DDTHH:mm:ss",
        "YYYY-MM-DDTHH:mm:ssZZ",
        "YYYY-MM-DD HH:mm:ss",
        "X",
        "x",
        "ddd, MMM D, YYYY",
    ]
    tzs = ["UTC", "US/Pacific", "Europe/Paris", "Asia/Tokyo", "+00:00", "+05:30", "-07:00"]

    fmt = fdp.PickValueInList(formats)
    tz = fdp.PickValueInList(tzs)

    _safe_get(text, fmt=fmt)
    _safe_get(text, tzinfo=tz)

    try:
        arrow_parser.Parser().parse_iso(text)
    except Exception:
        pass

    try:
        arrow_parser.Parser().parse(text)
    except Exception:
        pass

    dt = _safe_get(text)
    if dt is None:
        return

    try:
        dt.format(fmt)
    except Exception:
        pass

    try:
        dt.shift(
            days=fdp.ConsumeIntInRange(-10000, 10000),
            hours=fdp.ConsumeIntInRange(-1000, 1000),
            minutes=fdp.ConsumeIntInRange(-100000, 100000),
        )
    except Exception:
        pass

    try:
        dt.humanize(locale=fdp.PickValueInList(["en_us", "fr_fr", "es_es", "de_de", "ja_jp"]))
    except Exception:
        pass

    try:
        dt.dehumanize(text, locale=fdp.PickValueInList(["en_us", "fr_fr", "es_es"]))
    except Exception:
        pass

    try:
        dt.to(tz)
    except Exception:
        pass

    try:
        arrow_locales.get_locale(fdp.PickValueInList(["en_us", "en_gb", "fr_fr", "es_es", "pt_br", "de_de"]))
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
