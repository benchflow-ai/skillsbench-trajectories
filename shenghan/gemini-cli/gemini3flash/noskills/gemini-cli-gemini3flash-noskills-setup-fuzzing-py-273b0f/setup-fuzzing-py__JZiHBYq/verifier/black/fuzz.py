import atheris
import sys
import black

with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    input_str = fdp.ConsumeUnicodeNoSurrogates(4096)
    try:
        black.format_str(input_str, mode=black.Mode())
    except (black.parsing.InvalidInput, black.parsing.ASTSafetyError, SyntaxError, tokenize.TokenError, IndentationError):
        pass
    except Exception as e:
        # Unexpected exceptions could be bugs
        pass

import tokenize
def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
