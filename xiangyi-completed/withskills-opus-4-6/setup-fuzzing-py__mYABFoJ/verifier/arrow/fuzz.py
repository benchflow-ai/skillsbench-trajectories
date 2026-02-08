import atheris
import sys
import re

with atheris.instrument_imports():
    import arrow
    from arrow.parser import DateTimeParser, TzinfoParser, ParserError

# Pre-create objects that are reused across fuzz iterations
_parser = DateTimeParser()
_base_arrow = arrow.Arrow(2021, 1, 1)

# Common format tokens used by arrow
_FORMAT_TOKENS = [
    "YYYY", "YY", "MMMM", "MMM", "MM", "M",
    "DDDD", "DDD", "DD", "D", "Do",
    "dddd", "ddd", "dd", "d",
    "HH", "H", "hh", "h",
    "mm", "m", "ss", "s",
    "ZZZ", "ZZ", "Z",
    "a", "A",
    "X", "x",
    "W",
    "S", "SS", "SSS", "SSSS", "SSSSS", "SSSSSS",
]


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)

    # Choose which target to fuzz
    choice = fdp.ConsumeIntInRange(0, 4)

    if choice == 0:
        # Fuzz DateTimeParser.parse_iso()
        datetime_string = fdp.ConsumeUnicodeNoSurrogates(200)
        normalize_ws = fdp.ConsumeBool()
        try:
            _parser.parse_iso(datetime_string, normalize_whitespace=normalize_ws)
        except (ParserError, ValueError, TypeError, OverflowError, re.error):
            pass

    elif choice == 1:
        # Fuzz DateTimeParser.parse() with a generated format string
        datetime_string = fdp.ConsumeUnicodeNoSurrogates(200)
        # Build a format string from known tokens and fuzzed separators
        num_tokens = fdp.ConsumeIntInRange(1, 6)
        fmt_parts = []
        for _ in range(num_tokens):
            token_idx = fdp.ConsumeIntInRange(0, len(_FORMAT_TOKENS) - 1)
            fmt_parts.append(_FORMAT_TOKENS[token_idx])
            sep = fdp.ConsumeUnicodeNoSurrogates(3)
            fmt_parts.append(sep)
        fmt_str = "".join(fmt_parts)
        if not fmt_str.strip():
            return
        try:
            _parser.parse(datetime_string, fmt_str)
        except (ParserError, ValueError, TypeError, OverflowError, re.error):
            pass

    elif choice == 2:
        # Fuzz arrow.get() with string input
        input_string = fdp.ConsumeUnicodeNoSurrogates(200)
        try:
            arrow.get(input_string)
        except (ParserError, ValueError, TypeError, OverflowError):
            pass

    elif choice == 3:
        # Fuzz TzinfoParser.parse()
        tz_string = fdp.ConsumeUnicodeNoSurrogates(100)
        try:
            TzinfoParser.parse(tz_string)
        except (ParserError, ValueError, TypeError, OverflowError, KeyError):
            pass

    elif choice == 4:
        # Fuzz Arrow.dehumanize()
        input_string = fdp.ConsumeUnicodeNoSurrogates(200)
        try:
            _base_arrow.dehumanize(input_string)
        except (ParserError, ValueError, TypeError, OverflowError, re.error,
                AttributeError, KeyError):
            pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
