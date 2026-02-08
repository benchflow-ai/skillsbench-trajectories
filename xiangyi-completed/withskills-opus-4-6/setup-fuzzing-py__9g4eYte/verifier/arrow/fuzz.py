"""Coverage-guided fuzz driver for the Arrow library using Atheris (LibFuzzer)."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Arrow's date/time parsing functions."""
    fdp = atheris.FuzzedDataProvider(data)

    # Import inside to avoid affecting startup
    try:
        from arrow.parser import DateTimeParser, TzinfoParser
        import arrow
    except ImportError:
        return

    parser = DateTimeParser()
    input_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 512))

    # Fuzz DateTimeParser.parse_iso - primary ISO 8601 parser
    try:
        parser.parse_iso(input_str, normalize_whitespace=fdp.ConsumeBool())
    except Exception:
        pass

    # Fuzz DateTimeParser.parse with a format string
    fmt_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
    try:
        parser.parse(input_str, fmt_str)
    except Exception:
        pass

    # Fuzz TzinfoParser.parse - timezone string parsing
    tz_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
    try:
        TzinfoParser.parse(tz_str)
    except Exception:
        pass

    # Fuzz arrow.get with string input
    try:
        arrow.get(input_str)
    except Exception:
        pass

    # Fuzz Arrow.dehumanize with string input
    dehumanize_str = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
    try:
        arrow.utcnow().dehumanize(dehumanize_str)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
