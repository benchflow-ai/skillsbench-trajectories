import sys
import atheris


def TestOneInput(data: bytes):
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)
    s = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    if not s:
        return

    try:
        if choice == 0:
            # Fuzz the main entry point with a string argument
            arrow.get(s)
        elif choice == 1:
            # Fuzz ISO parsing
            from arrow.parser import DateTimeParser
            parser = DateTimeParser()
            parser.parse_iso(s)
        elif choice == 2:
            # Fuzz format-based parsing with common formats
            from arrow.parser import DateTimeParser
            parser = DateTimeParser()
            formats = [
                "YYYY-MM-DD",
                "YYYY-MM-DD HH:mm:ss",
                "YYYY/MM/DD",
                "MM-DD-YYYY",
                "DD.MM.YYYY",
                "YYYY-MM-DDTHH:mm:ssZ",
                "X",
            ]
            for fmt in formats:
                try:
                    parser.parse(s, fmt)
                except (arrow.parser.ParserError, arrow.parser.ParserMatchError):
                    pass
                except (ValueError, TypeError, OverflowError, re.error):
                    pass
        elif choice == 3:
            # Fuzz dehumanize
            now = arrow.utcnow()
            now.dehumanize(s)
    except (arrow.parser.ParserError, arrow.parser.ParserMatchError):
        pass
    except (ValueError, TypeError, OverflowError, KeyError, IndexError,
            AttributeError, ArithmeticError, UnicodeEncodeError,
            UnicodeDecodeError, RuntimeError, OSError, re.error):
        pass


def main():
    import re as _re_module
    global re
    re = _re_module
    atheris.instrument_all()
    global arrow
    import arrow as _arrow
    arrow = _arrow
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
