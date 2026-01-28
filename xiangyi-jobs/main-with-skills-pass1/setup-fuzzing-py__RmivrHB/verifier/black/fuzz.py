import sys
import atheris
from black import format_str, Mode, InvalidInput

def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        s = fdp.ConsumeUnicodeNoSurrogates(1024)
        format_str(s, mode=Mode())
    except InvalidInput:
        pass
    except Exception as e:
        # Unexpected exceptions could be bugs
        pass

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
