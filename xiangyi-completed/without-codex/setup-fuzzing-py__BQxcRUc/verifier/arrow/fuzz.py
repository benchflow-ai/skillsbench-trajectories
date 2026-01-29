import sys

import atheris

with atheris.instrument_imports():
    import arrow
    from arrow import parser as arrow_parser
    from arrow import util as arrow_util


COMMON_FORMATS = [
    "YYYY-MM-DD",
    "YYYY-MM-DD HH:mm:ss",
    "YYYY/MM/DD",
    "MM/DD/YYYY",
    "YYYY-MM-DDTHH:mm:ssZZ",
    "YYYY-MM-DDTHH:mm:ss.SSSZZ",
]


def _rand_format(fdp: atheris.FuzzedDataProvider) -> str:
    if fdp.ConsumeBool():
        return fdp.PickValueInList(COMMON_FORMATS)
    fmt = fdp.ConsumeUnicodeNoSurrogates(32)
    return fmt or "YYYY-MM-DD"


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    op = fdp.ConsumeIntInRange(0, 4)
    try:
        if op == 0:
            dt_str = fdp.ConsumeUnicodeNoSurrogates(128)
            if fdp.ConsumeBool():
                arrow.get(dt_str, _rand_format(fdp))
            else:
                arrow.get(dt_str)
        elif op == 1:
            ts = fdp.ConsumeFloat()
            arrow.get(ts)
        elif op == 2:
            base = arrow.utcnow()
            shift_kwargs = {}
            for unit in ("years", "months", "weeks", "days", "hours", "minutes", "seconds", "microseconds"):
                if fdp.ConsumeBool():
                    shift_kwargs[unit] = fdp.ConsumeIntInRange(-5, 5)
            shifted = base.shift(**shift_kwargs) if shift_kwargs else base
            fmt = _rand_format(fdp)
            shifted.format(fmt)
        elif op == 3:
            dt_str = fdp.ConsumeUnicodeNoSurrogates(128)
            fmt = _rand_format(fdp)
            arrow_parser.Parser().parse(dt_str, fmt)
        else:
            bounds = fdp.PickValueInList(["[]", "()", "[)", "(]", "", "invalid"])
            try:
                arrow_util.validate_bounds(bounds)
            except Exception:
                pass
            try:
                arrow_util.validate_ordinal(fdp.ConsumeIntInRange(-10, 400))
            except Exception:
                pass
            try:
                arrow_util.normalize_timestamp(fdp.ConsumeFloat())
            except Exception:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
