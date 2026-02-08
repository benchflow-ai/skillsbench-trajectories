"""Coverage-guided fuzz driver for the Arrow date/time library."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for Arrow's parsing functions."""
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError, ParserMatchError

    fdp = atheris.FuzzedDataProvider(data)

    # Split data into different test targets
    choice = fdp.ConsumeIntInRange(0, 4)
    input_str = fdp.ConsumeUnicode(fdp.remaining_bytes())

    if not input_str:
        return

    if choice == 0:
        # Fuzz arrow.get() with a string (ISO parsing path)
        try:
            arrow.get(input_str)
        except (arrow.parser.ParserError, arrow.parser.ParserMatchError,
                ValueError, OverflowError, TypeError):
            pass

    elif choice == 1:
        # Fuzz DateTimeParser.parse_iso() directly
        parser = DateTimeParser()
        try:
            parser.parse_iso(input_str)
        except (ParserError, ParserMatchError, ValueError, OverflowError):
            pass

    elif choice == 2:
        # Fuzz TzinfoParser.parse()
        try:
            TzinfoParser.parse(input_str)
        except (ParserError, ValueError, OverflowError, OSError, KeyError):
            pass

    elif choice == 3:
        # Fuzz DateTimeParser.parse() with various format strings
        parser = DateTimeParser()
        formats = [
            "YYYY-MM-DD",
            "YYYY-MM-DD HH:mm:ss",
            "YYYY/MM/DD",
            "MM-DD-YYYY",
            "DD.MM.YYYY HH:mm",
            "YYYY-MM-DDTHH:mm:ssZ",
            "X",
            "MMMM DD, YYYY",
            "ddd MMM DD HH:mm:ss YYYY",
        ]
        for fmt in formats:
            try:
                parser.parse(input_str, fmt)
            except (ParserError, ParserMatchError, ValueError, OverflowError):
                pass

    elif choice == 4:
        # Fuzz Arrow.dehumanize()
        try:
            now = arrow.utcnow()
            now.dehumanize(input_str)
        except (ValueError, OverflowError, AttributeError, ParserError):
            pass


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
