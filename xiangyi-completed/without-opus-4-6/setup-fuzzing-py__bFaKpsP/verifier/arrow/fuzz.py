"""Coverage-guided fuzzer for the Arrow date/time library."""

import sys
import atheris


def TestOneInput(data):
    """Fuzz target for Arrow's parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
    if not text:
        return

    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser

    # Fuzz arrow.get() with string input
    try:
        arrow.get(text)
    except Exception:
        pass

    # Fuzz ISO parsing directly
    parser = DateTimeParser()
    try:
        parser.parse_iso(text)
    except Exception:
        pass

    # Fuzz format-based parsing with a few common formats
    formats = [
        "YYYY-MM-DD",
        "YYYY-MM-DD HH:mm:ss",
        "YYYY/MM/DD",
        "DD.MM.YYYY",
        "X",
        "HH:mm",
        "MMMM D, YYYY",
    ]
    for fmt in formats:
        try:
            parser.parse(text, fmt)
        except Exception:
            pass

    # Fuzz timezone parsing
    try:
        TzinfoParser.parse(text)
    except Exception:
        pass

    # Fuzz dehumanize
    try:
        now = arrow.utcnow()
        now.dehumanize(text)
    except Exception:
        pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
