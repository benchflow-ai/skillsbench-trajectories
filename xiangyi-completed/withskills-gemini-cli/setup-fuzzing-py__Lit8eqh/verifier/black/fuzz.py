import atheris
import sys

with atheris.instrument_imports():
    import black
    from black.mode import Mode
    from black.parsing import InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        mode = Mode()
        try:
            formatted = black.format_str(src, mode=mode)
            # Idempotency check
            formatted_again = black.format_str(formatted, mode=mode)
            if formatted != formatted_again:
                raise RuntimeError(f"Idempotency violated!\nOriginal: {src!r}\nFirst pass: {formatted!r}\nSecond pass: {formatted_again!r}")
        except (InvalidInput, tokenize.TokenError, IndentationError, SyntaxError, KeyError):
            pass
    except Exception as e:
        if "tokenize" in str(e) or "IndentationError" in str(e) or "SyntaxError" in str(e) or isinstance(e, KeyError):
            pass
        else:
            raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    # We need to import tokenize to catch its errors
    import tokenize
    main()
