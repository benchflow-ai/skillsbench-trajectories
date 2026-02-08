"""Coverage-guided fuzzer for the Arrow date/time library using atheris + LibFuzzer."""

import sys
import atheris


def TestOneInput(data: bytes):
    """Fuzz target for arrow's parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser

    text = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))
    if not text:
        return

    # Fuzz arrow.get() with a string
    try:
        arrow.get(text)
    except Exception:
        pass

    # Fuzz ISO 8601 parsing
    parser = DateTimeParser()
    try:
        parser.parse_iso(text)
    except Exception:
        pass

    # Fuzz custom format parsing with a generated format string
    fmt = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
    if fmt:
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

    # Fuzz format string processing
    try:
        now = arrow.utcnow()
        now.format(text)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
