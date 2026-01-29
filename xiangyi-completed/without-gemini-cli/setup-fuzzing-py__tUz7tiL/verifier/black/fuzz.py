import atheris
import sys
import black
from black.mode import Mode

with atheris.instrument_imports():
    import black

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        # Fuzz black.format_str(string)
        src = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
        black.format_str(src, mode=Mode())
    except (black.parsing.InvalidInput, black.parsing.ASTSafetyError):
        pass
    except Exception as e:
        # Unexpected crash
        # print(f"Unexpected exception: {e}")
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
