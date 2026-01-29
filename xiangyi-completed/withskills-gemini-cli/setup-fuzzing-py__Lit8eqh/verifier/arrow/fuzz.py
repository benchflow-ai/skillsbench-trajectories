import atheris
import sys

with atheris.instrument_imports():
    from arrow.parser import DateTimeParser, ParserError, ParserMatchError

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    parser = DateTimeParser()

    try:
        # Fuzz parse_iso
        iso_str = fdp.ConsumeUnicodeNoSurrogates(128)
        try:
            parser.parse_iso(iso_str)
        except (ParserError, ValueError, TypeError):
            pass

        # Fuzz parse
        fmt = fdp.ConsumeUnicodeNoSurrogates(32)
        dt_str = fdp.ConsumeUnicodeNoSurrogates(128)
        try:
            parser.parse(dt_str, fmt)
        except (ParserError, ParserMatchError, ValueError, TypeError):
            pass
        except Exception as e:
            # We want to catch unexpected exceptions
            # but regex errors from invalid formats are somewhat expected if not handled
            if "regular expression" in str(e):
                pass
            else:
                raise e

    except Exception:
        # Any other exception is a bug
        raise

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
