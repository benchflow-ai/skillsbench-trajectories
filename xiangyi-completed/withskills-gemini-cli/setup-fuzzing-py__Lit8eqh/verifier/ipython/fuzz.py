import atheris
import sys
import warnings

with atheris.instrument_imports():
    from IPython.core.inputtransformer2 import TransformerManager

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        cell = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        tm = TransformerManager()
        try:
            # We wrap this in catch_warnings because it might emit a lot of them
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tm.transform_cell(cell)
        except (SyntaxError, IndentationError, tokenize.TokenError):
            pass
        except RuntimeError as e:
            if "Input transformation still changing" in str(e):
                pass
            else:
                raise e
    except Exception as e:
        if "tokenize" in str(e) or "IndentationError" in str(e) or "SyntaxError" in str(e):
            pass
        else:
            raise e

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    import tokenize
    main()
