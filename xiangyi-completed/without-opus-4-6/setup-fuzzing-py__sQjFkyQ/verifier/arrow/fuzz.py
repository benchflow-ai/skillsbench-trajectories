import sys
import atheris


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser

    # Fuzz arrow.get() with string input
    try:
        arrow.get(s)
    except Exception:
        pass

    # Fuzz DateTimeParser.parse_iso()
    try:
        parser = DateTimeParser()
        parser.parse_iso(s)
    except Exception:
        pass

    # Fuzz TzinfoParser.parse()
    try:
        tz_parser = TzinfoParser()
        tz_parser.parse(s)
    except Exception:
        pass

    # Fuzz arrow.get() with numeric-like input
    try:
        val = fdp.ConsumeFloat()
        arrow.get(val)
    except Exception:
        pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
