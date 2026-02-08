import sys
import atheris

with atheris.instrument_imports():
    import re
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError

# Acceptable exceptions that indicate normal rejection of invalid input
ACCEPTABLE_EXCEPTIONS = (
    ParserError,
    ValueError,
    TypeError,
    OverflowError,
    re.error,
    OSError,
)


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    # --- Target 1: arrow.get() with a single fuzz string (ISO parsing) ---
    s1 = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        arrow.get(s1)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    # --- Target 2: arrow.get() with two fuzz strings (format parsing) ---
    s2 = fdp.ConsumeUnicodeNoSurrogates(256)
    s3 = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        arrow.get(s2, s3)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    # --- Target 3: DateTimeParser.parse_iso() with fuzz string ---
    s4 = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        parser = DateTimeParser()
        parser.parse_iso(s4)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    # --- Target 4: DateTimeParser.parse() with fuzz string + format string ---
    s5 = fdp.ConsumeUnicodeNoSurrogates(256)
    s6 = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        parser = DateTimeParser()
        parser.parse(s5, s6)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    # --- Target 5: TzinfoParser.parse() with fuzz string ---
    s7 = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        TzinfoParser.parse(s7)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    # --- Target 6: Arrow.dehumanize() with fuzz string ---
    s8 = fdp.ConsumeUnicodeNoSurrogates(256)
    try:
        arrow.Arrow.utcnow().dehumanize(s8)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    # --- Target 7: Arrow.fromtimestamp() with numeric values ---
    fuzz_float = fdp.ConsumeFloat()
    try:
        arrow.Arrow.fromtimestamp(fuzz_float)
    except ACCEPTABLE_EXCEPTIONS:
        pass

    fuzz_int = fdp.ConsumeInt(8)
    try:
        arrow.Arrow.fromtimestamp(fuzz_int)
    except ACCEPTABLE_EXCEPTIONS:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
